"""OrthoFlow API — Phase 4a Imaging Suite Routes.

Main imaging endpoints: upload, view, list, delete, series management.
All endpoints are practice-scoped via JWT. Files stored in MinIO.
"""
import hashlib
import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import get_db
from app.models.imaging import PatientImage, ImagingSeries
from app.services.storage import upload_file, download_file, get_presigned_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/imaging", tags=["imaging"])

# ── Constants ─────────────────────────────────────────────────────────────────

IMAGING_BUCKET = "orthoflow-imaging"
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_CONTENT_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/tiff": "tiff",
    "application/dicom": "dcm",
    "application/octet-stream": "dcm",  # DICOM often sent as octet-stream
}
ALLOWED_IMAGE_TYPES = [
    "pano", "ceph", "periapical", "bitewing", "cbct", "photo_intraoral",
    "photo_extraoral", "photo_smile", "full_mouth_series", "occlusal", "other",
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class ImageResponse(BaseModel):
    id: str
    patient_id: str
    series_id: str | None
    image_type: str
    modality: str | None
    description: str | None
    tooth_numbers: str | None
    file_name: str
    file_size_bytes: int | None
    content_type: str | None
    status: str
    source: str
    captured_date: str
    created_at: str
    view_url: str | None = None


class SeriesCreate(BaseModel):
    patient_id: str = Field(..., description="Patient UUID")
    series_type: str = Field(..., min_length=1, max_length=30)
    captured_date: date
    appointment_id: str | None = None
    description: str | None = Field(None, max_length=300)
    notes: str | None = None


class SeriesResponse(BaseModel):
    id: str
    patient_id: str
    series_type: str
    description: str | None
    image_count: int
    captured_date: str
    notes: str | None
    created_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _image_to_response(image: PatientImage, view_url: str | None = None) -> dict:
    return {
        "id": str(image.id),
        "patient_id": str(image.patient_id),
        "series_id": str(image.series_id) if image.series_id else None,
        "image_type": image.image_type,
        "modality": image.modality,
        "description": image.description,
        "tooth_numbers": image.tooth_numbers,
        "file_name": image.file_name,
        "file_size_bytes": image.file_size_bytes,
        "content_type": image.content_type,
        "status": image.status,
        "source": image.source,
        "captured_date": image.captured_date.isoformat(),
        "created_at": image.created_at.isoformat() if image.created_at else "",
        "view_url": view_url,
    }


def _series_to_response(series: ImagingSeries) -> dict:
    return {
        "id": str(series.id),
        "patient_id": str(series.patient_id),
        "series_type": series.series_type,
        "description": series.description,
        "image_count": series.image_count,
        "captured_date": series.captured_date.isoformat(),
        "notes": series.notes,
        "created_at": series.created_at.isoformat() if series.created_at else "",
    }


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    image_type: str = Form(...),
    patient_id: str = Form(...),
    series_id: str | None = Form(None),
    tooth_numbers: str | None = Form(None),
    description: str | None = Form(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an imaging file (DICOM, PNG, JPG, TIFF). Max 500MB."""
    practice_id = current_user["practice_id"]

    # Validate image_type
    if image_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image_type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. Accepted: DICOM, PNG, JPG, TIFF.",
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 500MB.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    # Compute checksum
    checksum = hashlib.sha256(content).hexdigest()

    # Build storage path: {practice_id}/{patient_id}/{date}/{filename}
    today_str = date.today().isoformat()
    filename = file.filename or f"image_{uuid.uuid4().hex[:8]}.{ALLOWED_CONTENT_TYPES[content_type]}"
    # Sanitize filename
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    if not safe_filename:
        safe_filename = f"image_{uuid.uuid4().hex[:8]}"
    storage_path = f"{practice_id}/{patient_id}/{today_str}/{safe_filename}"

    # Upload to MinIO
    try:
        await upload_file(storage_path, content, content_type)
    except Exception as e:
        logger.error("imaging_upload_failed", extra={
            "practice_id": practice_id,
            "patient_id": patient_id,
            "error": str(e),
        })
        raise HTTPException(status_code=502, detail="Failed to store file. Please retry.")

    # Create PatientImage record
    image_id = uuid.uuid4()
    image = PatientImage(
        id=image_id,
        practice_id=practice_id,
        patient_id=patient_id,
        series_id=series_id if series_id else None,
        image_type=image_type,
        description=description,
        tooth_numbers=tooth_numbers,
        storage_path=storage_path,
        storage_bucket=IMAGING_BUCKET,
        file_name=safe_filename,
        file_size_bytes=len(content),
        content_type=content_type,
        checksum_sha256=checksum,
        source="upload",
        status="active",
        captured_date=date.today(),
        uploaded_by=current_user["user_id"],
    )
    db.add(image)

    # If part of a series, increment image_count
    if series_id:
        series_result = await db.execute(
            select(ImagingSeries).where(
                ImagingSeries.id == series_id,
                ImagingSeries.practice_id == practice_id,
            )
        )
        series = series_result.scalar_one_or_none()
        if series:
            series.image_count = (series.image_count or 0) + 1

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=current_user["user_id"],
        action="image.upload",
        resource_type="patient_image",
        resource_id=str(image_id),
        details=f"Uploaded {image_type} for patient {patient_id} ({safe_filename}, {len(content)} bytes)",
    )
    await db.commit()

    logger.info("imaging_upload_success", extra={
        "image_id": str(image_id),
        "practice_id": practice_id,
        "patient_id": patient_id,
        "image_type": image_type,
        "file_size": len(content),
    })

    return {
        "id": str(image_id),
        "status": "uploaded",
        "file_name": safe_filename,
        "file_size_bytes": len(content),
        "checksum_sha256": checksum,
        "storage_path": storage_path,
    }


# ── View (stream file) ───────────────────────────────────────────────────────

@router.get("/view/{image_id}")
async def view_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream image file directly from MinIO (auth-protected)."""
    practice_id = current_user["practice_id"]

    result = await db.execute(
        select(PatientImage).where(
            PatientImage.id == image_id,
            PatientImage.practice_id == practice_id,
            PatientImage.status != "deleted",
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        file_content = await download_file(image.storage_path)
    except Exception as e:
        logger.error("imaging_download_failed", extra={
            "image_id": image_id,
            "storage_path": image.storage_path,
            "error": str(e),
        })
        raise HTTPException(status_code=502, detail="Failed to retrieve file from storage.")

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=current_user["user_id"],
        action="image.view",
        resource_type="patient_image",
        resource_id=str(image_id),
    )
    await db.commit()

    media_type = image.content_type or "application/octet-stream"
    return StreamingResponse(
        iter([file_content]),
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{image.file_name}"',
            "Content-Length": str(len(file_content)),
        },
    )


# ── List images for patient ───────────────────────────────────────────────────

@router.get("/patients/{patient_id}")
async def list_patient_images(
    patient_id: str,
    image_type: str | None = Query(None, description="Filter by image type"),
    date_from: date | None = Query(None, description="Filter from date (inclusive)"),
    date_to: date | None = Query(None, description="Filter to date (inclusive)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all images for a patient, with optional filters."""
    practice_id = current_user["practice_id"]

    conditions = [
        PatientImage.practice_id == practice_id,
        PatientImage.patient_id == patient_id,
        PatientImage.status != "deleted",
    ]
    if image_type:
        conditions.append(PatientImage.image_type == image_type)
    if date_from:
        conditions.append(PatientImage.captured_date >= date_from)
    if date_to:
        conditions.append(PatientImage.captured_date <= date_to)

    result = await db.execute(
        select(PatientImage)
        .where(and_(*conditions))
        .order_by(PatientImage.captured_date.desc(), PatientImage.created_at.desc())
    )
    images = result.scalars().all()

    # Build response with view URLs (route-based, no presign complexity)
    response_images = []
    for img in images:
        view_url = f"/api/v1/imaging/view/{img.id}"
        response_images.append(_image_to_response(img, view_url=view_url))

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=current_user["user_id"],
        action="image.list",
        resource_type="patient_image",
        details=f"Listed images for patient {patient_id} ({len(response_images)} results)",
    )
    await db.commit()

    return {"images": response_images, "total": len(response_images)}


# ── Single image detail ───────────────────────────────────────────────────────

@router.get("/{image_id}")
async def get_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single image detail with view URL."""
    practice_id = current_user["practice_id"]

    result = await db.execute(
        select(PatientImage).where(
            PatientImage.id == image_id,
            PatientImage.practice_id == practice_id,
            PatientImage.status != "deleted",
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    view_url = f"/api/v1/imaging/view/{image.id}"

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=current_user["user_id"],
        action="image.view_detail",
        resource_type="patient_image",
        resource_id=str(image_id),
    )
    await db.commit()

    return _image_to_response(image, view_url=view_url)


# ── Soft delete ───────────────────────────────────────────────────────────────

@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete an image (sets status to 'deleted')."""
    practice_id = current_user["practice_id"]

    result = await db.execute(
        select(PatientImage).where(
            PatientImage.id == image_id,
            PatientImage.practice_id == practice_id,
            PatientImage.status != "deleted",
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    image.status = "deleted"

    # Decrement series count if applicable
    if image.series_id:
        series_result = await db.execute(
            select(ImagingSeries).where(ImagingSeries.id == image.series_id)
        )
        series = series_result.scalar_one_or_none()
        if series and series.image_count > 0:
            series.image_count -= 1

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=current_user["user_id"],
        action="image.delete",
        resource_type="patient_image",
        resource_id=str(image_id),
        details=f"Soft deleted image {image.file_name}",
    )
    await db.commit()

    return {"id": str(image_id), "status": "deleted"}


# ── Series management ─────────────────────────────────────────────────────────

@router.post("/series", status_code=201)
async def create_series(
    payload: SeriesCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an imaging series to group related images."""
    practice_id = current_user["practice_id"]

    series_id = uuid.uuid4()
    series = ImagingSeries(
        id=series_id,
        practice_id=practice_id,
        patient_id=payload.patient_id,
        appointment_id=payload.appointment_id if payload.appointment_id else None,
        series_type=payload.series_type,
        description=payload.description,
        captured_date=payload.captured_date,
        captured_by=current_user["user_id"],
        notes=payload.notes,
        image_count=0,
    )
    db.add(series)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=current_user["user_id"],
        action="series.create",
        resource_type="imaging_series",
        resource_id=str(series_id),
        details=f"Created {payload.series_type} series for patient {payload.patient_id}",
    )
    await db.commit()

    return _series_to_response(series)


@router.get("/series/{patient_id}")
async def list_patient_series(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all imaging series for a patient."""
    practice_id = current_user["practice_id"]

    result = await db.execute(
        select(ImagingSeries)
        .where(
            ImagingSeries.practice_id == practice_id,
            ImagingSeries.patient_id == patient_id,
        )
        .order_by(ImagingSeries.captured_date.desc())
    )
    series_list = result.scalars().all()

    return {
        "series": [_series_to_response(s) for s in series_list],
        "total": len(series_list),
    }
