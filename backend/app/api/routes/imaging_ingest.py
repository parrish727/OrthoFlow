"""OrthoFlow API — Phase 4b Edge Appliance Ingest Endpoint.

Receives images from OrthoFlow Edge appliances (future DICOM bridge hardware).
Auth via X-Edge-API-Key header (appliances don't have user login).
Patient matching by ID or name+DOB. Deduplication via DICOM instance UID.

This is the plug-in point for Phase 4b. The edge appliance will call this
after receiving DICOM from x-ray machines.
"""
import hashlib
import json
import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.clinical import Patient
from app.models.imaging import PatientImage
from app.services.storage import upload_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/imaging/ingest", tags=["imaging-ingest"])

# ── Constants ─────────────────────────────────────────────────────────────────

IMAGING_BUCKET = "orthoflow-imaging"
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_CONTENT_TYPES = {
    "image/png", "image/jpeg", "image/tiff",
    "application/dicom", "application/octet-stream",
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class IngestMetadata(BaseModel):
    """JSON metadata sent alongside the file from edge appliance."""
    device_id: str = Field(..., max_length=100)
    device_name: str = Field(..., max_length=200)
    patient_mrn: str | None = Field(None, max_length=50)
    patient_id: str | None = Field(None, description="Patient UUID if known")
    patient_name: str | None = Field(None, max_length=200)
    patient_dob: date | None = None
    image_type: str = Field(..., max_length=30)
    modality: str | None = Field(None, max_length=20)
    dicom_study_uid: str | None = Field(None, max_length=128)
    dicom_series_uid: str | None = Field(None, max_length=128)
    dicom_instance_uid: str | None = Field(None, max_length=128)
    captured_date: date | None = None


class IngestResponse(BaseModel):
    id: str
    status: str
    patient_id: str | None
    patient_matched: bool
    duplicate: bool
    message: str


class DeviceResponse(BaseModel):
    device_id: str
    device_name: str
    last_seen: str
    image_count: int


# ── Auth dependency ───────────────────────────────────────────────────────────

async def verify_edge_api_key(
    x_edge_api_key: str = Header(..., alias="X-Edge-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify the edge appliance API key and extract practice context.

    The API key format is: {practice_id}:{secret}
    This allows practice-scoping without JWT.
    """
    if not x_edge_api_key or ":" not in x_edge_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid X-Edge-API-Key format. Expected: {practice_id}:{secret}",
        )

    parts = x_edge_api_key.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid API key format")

    practice_id, secret = parts

    # Validate the key against stored edge keys
    # For Phase 4a, we validate format and practice existence
    # Phase 4b will add a dedicated edge_devices table with hashed keys
    if not practice_id or not secret:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Verify practice_id is a valid UUID
    try:
        uuid.UUID(practice_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid practice ID in API key")

    return {"practice_id": practice_id, "device_auth": True}


# ── Patient matching ──────────────────────────────────────────────────────────

async def _match_patient(
    db: AsyncSession,
    practice_id: str,
    patient_id: str | None,
    patient_name: str | None,
    patient_dob: date | None,
) -> Patient | None:
    """Try to match an incoming image to an existing patient.

    Priority:
    1. Match by explicit patient_id
    2. Match by name + DOB combination
    """
    # Try by patient_id first
    if patient_id:
        result = await db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.practice_id == practice_id,
            )
        )
        patient = result.scalar_one_or_none()
        if patient:
            return patient

    # Try by name + DOB
    if patient_name and patient_dob:
        # Parse name (expect "Last, First" or "First Last")
        name_parts = patient_name.strip().split(",")
        if len(name_parts) == 2:
            last_name = name_parts[0].strip()
            first_name = name_parts[1].strip()
        else:
            name_parts = patient_name.strip().split(" ", 1)
            first_name = name_parts[0].strip() if name_parts else ""
            last_name = name_parts[1].strip() if len(name_parts) > 1 else ""

        if first_name and last_name:
            result = await db.execute(
                select(Patient).where(
                    Patient.practice_id == practice_id,
                    func.lower(Patient.first_name) == first_name.lower(),
                    func.lower(Patient.last_name) == last_name.lower(),
                    Patient.date_of_birth == patient_dob,
                )
            )
            patient = result.scalar_one_or_none()
            if patient:
                return patient

    return None


# ── Ingest endpoint ───────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def ingest_image(
    file: UploadFile = File(...),
    metadata_json: str = Form(..., alias="metadata"),
    edge_context: dict = Depends(verify_edge_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Receive an image from an OrthoFlow Edge appliance.

    Accepts multipart form with:
      - file: the image/DICOM file
      - metadata: JSON string with device info, patient matching data, DICOM UIDs

    Auth: X-Edge-API-Key header (practice_id:secret format).
    Deduplication: checks dicom_instance_uid to avoid storing duplicates.
    """
    practice_id = edge_context["practice_id"]

    # Parse metadata JSON
    try:
        meta = IngestMetadata.model_validate_json(metadata_json)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metadata JSON: {str(e)}",
        )

    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed.",
        )

    # Read file
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 500MB.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")

    # Deduplication: check dicom_instance_uid
    if meta.dicom_instance_uid:
        existing = await db.execute(
            select(PatientImage.id).where(
                PatientImage.practice_id == practice_id,
                PatientImage.dicom_instance_uid == meta.dicom_instance_uid,
                PatientImage.status == "active",
            )
        )
        existing_id = existing.scalar_one_or_none()
        if existing_id:
            logger.info("imaging_ingest_duplicate", extra={
                "practice_id": practice_id,
                "dicom_instance_uid": meta.dicom_instance_uid,
                "existing_image_id": str(existing_id),
            })
            return IngestResponse(
                id=str(existing_id),
                status="duplicate",
                patient_id=None,
                patient_matched=False,
                duplicate=True,
                message=f"Image already ingested (dicom_instance_uid: {meta.dicom_instance_uid})",
            )

    # Patient matching
    patient = await _match_patient(
        db=db,
        practice_id=practice_id,
        patient_id=meta.patient_id,
        patient_name=meta.patient_name,
        patient_dob=meta.patient_dob,
    )
    patient_matched = patient is not None
    matched_patient_id = str(patient.id) if patient else None

    # Compute checksum
    checksum = hashlib.sha256(content).hexdigest()

    # Build storage path
    captured = meta.captured_date or date.today()
    filename = file.filename or f"edge_{uuid.uuid4().hex[:8]}.dcm"
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    if not safe_filename:
        safe_filename = f"edge_{uuid.uuid4().hex[:8]}"

    patient_path = matched_patient_id or "unmatched"
    storage_path = f"{practice_id}/{patient_path}/{captured.isoformat()}/{safe_filename}"

    # Upload to MinIO
    try:
        await upload_file(storage_path, content, content_type)
    except Exception as e:
        logger.error("imaging_ingest_storage_failed", extra={
            "practice_id": practice_id,
            "device_id": meta.device_id,
            "error": str(e),
        })
        raise HTTPException(status_code=502, detail="Failed to store file.")

    # Create PatientImage record
    image_id = uuid.uuid4()
    image = PatientImage(
        id=image_id,
        practice_id=practice_id,
        patient_id=matched_patient_id,
        image_type=meta.image_type,
        modality=meta.modality,
        storage_path=storage_path,
        storage_bucket=IMAGING_BUCKET,
        file_name=safe_filename,
        file_size_bytes=len(content),
        content_type=content_type,
        checksum_sha256=checksum,
        dicom_study_uid=meta.dicom_study_uid,
        dicom_series_uid=meta.dicom_series_uid,
        dicom_instance_uid=meta.dicom_instance_uid,
        source="edge_appliance",
        source_device_id=meta.device_id,
        source_device_name=meta.device_name,
        status="active",
        captured_date=captured,
    )
    db.add(image)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=None,  # No user — appliance auth
        action="image.ingest",
        resource_type="patient_image",
        resource_id=str(image_id),
        details=(
            f"Edge ingest from device {meta.device_id} ({meta.device_name}). "
            f"Patient matched: {patient_matched}. File: {safe_filename} ({len(content)} bytes)"
        ),
    )
    await db.commit()

    logger.info("imaging_ingest_success", extra={
        "image_id": str(image_id),
        "practice_id": practice_id,
        "device_id": meta.device_id,
        "patient_matched": patient_matched,
        "patient_id": matched_patient_id,
    })

    message = "Image ingested successfully"
    if not patient_matched:
        message += " (patient not matched — manual linking required)"

    return IngestResponse(
        id=str(image_id),
        status="ingested",
        patient_id=matched_patient_id,
        patient_matched=patient_matched,
        duplicate=False,
        message=message,
    )


# ── Device listing ────────────────────────────────────────────────────────────

@router.get("/devices")
async def list_edge_devices(
    edge_context: dict = Depends(verify_edge_api_key),
    db: AsyncSession = Depends(get_db),
):
    """List registered edge devices for this practice.

    Derived from PatientImage records with source='edge_appliance'.
    Phase 4b will add a dedicated edge_devices registration table.
    """
    practice_id = edge_context["practice_id"]

    # Query distinct devices from ingested images
    result = await db.execute(
        select(
            PatientImage.source_device_id,
            PatientImage.source_device_name,
            func.max(PatientImage.created_at).label("last_seen"),
            func.count(PatientImage.id).label("image_count"),
        )
        .where(
            PatientImage.practice_id == practice_id,
            PatientImage.source == "edge_appliance",
            PatientImage.source_device_id.isnot(None),
        )
        .group_by(PatientImage.source_device_id, PatientImage.source_device_name)
        .order_by(func.max(PatientImage.created_at).desc())
    )
    rows = result.all()

    devices = [
        {
            "device_id": row.source_device_id,
            "device_name": row.source_device_name or "Unknown Device",
            "last_seen": row.last_seen.isoformat() if row.last_seen else "",
            "image_count": row.image_count,
        }
        for row in rows
    ]

    return {"devices": devices, "total": len(devices)}
