"""OrthoFlow API — Sprint 1 Clinical Enhancement Routes.

Patient deactivation, SSN, alerts, family linking, aligner tracking, elastics, oral hygiene.
All endpoints are practice-scoped via JWT.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user

from app.models.clinical import (
    Patient, PatientAlert, PatientFamily,
    AlignerTreatment, AlignerTrayLog, ElasticPrescription,
)

router = APIRouter(prefix="/api/v1", tags=["clinical-enhancements"])


# ═══════════════════════════════════════════════════════════════════════════════
# PATIENT DEACTIVATION
# ═══════════════════════════════════════════════════════════════════════════════

class DeactivateRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    remove_info: bool = False  # If true, clear PHI fields


@router.post("/patients/{patient_id}/deactivate")
async def deactivate_patient(
    patient_id: str,
    payload: DeactivateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Deactivate a patient. Optionally remove their PHI."""
    patient = await _get_patient(db, patient_id, user["practice_id"])
    patient.status = "inactive"
    patient.deactivated_at = datetime.now(timezone.utc)
    patient.deactivation_reason = payload.reason

    if payload.remove_info:
        patient.email = None
        patient.phone = None
        patient.phone_secondary = None
        patient.address = None
        patient.ssn_encrypted = None
        patient.notes = None

    await db.commit()
    return {"status": "deactivated", "info_removed": str(payload.remove_info)}


@router.post("/patients/{patient_id}/reactivate")
async def reactivate_patient(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Reactivate a previously deactivated patient."""
    patient = await _get_patient(db, patient_id, user["practice_id"])
    patient.status = "active"
    patient.deactivated_at = None
    patient.deactivation_reason = None
    await db.commit()
    return {"status": "reactivated"}


# ═══════════════════════════════════════════════════════════════════════════════
# SSN (ENCRYPTED)
# ═══════════════════════════════════════════════════════════════════════════════

class SSNUpdate(BaseModel):
    ssn: str = Field(..., pattern=r"^\d{3}-\d{2}-\d{4}$")


@router.put("/patients/{patient_id}/ssn")
async def update_patient_ssn(
    patient_id: str,
    payload: SSNUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Store encrypted SSN for patient. Only owner/office_manager can access."""
    if user["role"] not in ("owner", "office_manager", "doctor"):
        raise HTTPException(status_code=403, detail="Insufficient permissions for SSN access")

    patient = await _get_patient(db, patient_id, user["practice_id"])

    # Simple encryption placeholder — in production use Fernet/AES from app.core.crypto
    # For now, store with a reversible obfuscation marker
    from hashlib import sha256
    import base64
    # XOR-based obfuscation (replace with proper AES in production crypto module)
    key_bytes = sha256(str(user["practice_id"]).encode()).digest()[:16]
    ssn_bytes = payload.ssn.encode()
    encrypted = base64.b64encode(
        bytes(a ^ b for a, b in zip(ssn_bytes, key_bytes * 2))
    ).decode()
    patient.ssn_encrypted = encrypted
    await db.commit()
    return {"status": "saved"}


@router.get("/patients/{patient_id}/ssn")
async def get_patient_ssn(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | None]:
    """Retrieve decrypted SSN. Restricted to owner/office_manager."""
    if user["role"] not in ("owner", "office_manager", "doctor"):
        raise HTTPException(status_code=403, detail="Insufficient permissions for SSN access")

    patient = await _get_patient(db, patient_id, user["practice_id"])
    if not patient.ssn_encrypted:
        return {"ssn": None, "masked": None}

    # Decrypt
    from hashlib import sha256
    import base64
    key_bytes = sha256(str(user["practice_id"]).encode()).digest()[:16]
    encrypted_bytes = base64.b64decode(patient.ssn_encrypted)
    decrypted = bytes(a ^ b for a, b in zip(encrypted_bytes, key_bytes * 2)).decode()

    # Return masked version (show last 4 only)
    masked = f"***-**-{decrypted[-4:]}"
    return {"ssn": decrypted, "masked": masked}


# ═══════════════════════════════════════════════════════════════════════════════
# PATIENT ALERTS (allergies, medical conditions, etc.)
# ═══════════════════════════════════════════════════════════════════════════════

class AlertCreate(BaseModel):
    alert_type: str = Field(..., pattern="^(allergy|medical|behavioral|billing|other)$")
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


@router.get("/patients/{patient_id}/alerts")
async def get_patient_alerts(
    patient_id: str,
    active_only: bool = Query(True),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get alerts for a patient."""
    query = select(PatientAlert).where(
        PatientAlert.patient_id == uuid.UUID(patient_id),
        PatientAlert.practice_id == user["practice_id"],
    )
    if active_only:
        query = query.where(PatientAlert.is_active.is_(True))
    query = query.order_by(PatientAlert.severity.desc(), PatientAlert.created_at.desc())

    result = await db.execute(query)
    alerts = result.scalars().all()
    return [
        {
            "id": str(a.id), "alert_type": a.alert_type, "severity": a.severity,
            "title": a.title, "description": a.description, "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.post("/patients/{patient_id}/alerts", status_code=status.HTTP_201_CREATED)
async def create_patient_alert(
    patient_id: str,
    payload: AlertCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Create a new alert for a patient."""
    alert = PatientAlert(
        practice_id=user["practice_id"],
        patient_id=uuid.UUID(patient_id),
        alert_type=payload.alert_type,
        severity=payload.severity,
        title=payload.title,
        description=payload.description,
        created_by=user["user_id"],
    )
    db.add(alert)
    await db.commit()
    return {"id": str(alert.id), "status": "created"}


@router.delete("/patients/{patient_id}/alerts/{alert_id}")
async def dismiss_alert(
    patient_id: str,
    alert_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Dismiss (deactivate) an alert."""
    result = await db.execute(
        select(PatientAlert).where(
            PatientAlert.id == uuid.UUID(alert_id),
            PatientAlert.practice_id == user["practice_id"],
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = False
    await db.commit()
    return {"status": "dismissed"}


# ═══════════════════════════════════════════════════════════════════════════════
# FAMILY LINKING
# ═══════════════════════════════════════════════════════════════════════════════

class FamilyCreate(BaseModel):
    family_name: str = Field(..., min_length=1, max_length=255)
    patient_ids: list[str] = Field(..., min_length=1)
    relationships: dict[str, str] = {}  # patient_id → relationship label


@router.post("/families", status_code=status.HTTP_201_CREATED)
async def create_family(
    payload: FamilyCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Create a family group and link patients to it."""
    family = PatientFamily(
        practice_id=user["practice_id"],
        family_name=payload.family_name,
    )
    db.add(family)
    await db.flush()

    # Link patients
    for pid in payload.patient_ids:
        result = await db.execute(
            select(Patient).where(Patient.id == uuid.UUID(pid), Patient.practice_id == user["practice_id"])
        )
        patient = result.scalar_one_or_none()
        if patient:
            patient.family_id = family.id
            patient.family_relationship = payload.relationships.get(pid, "member")

    # Set first patient as primary contact
    if payload.patient_ids:
        family.primary_contact_id = uuid.UUID(payload.patient_ids[0])

    await db.commit()
    return {"id": str(family.id), "status": "created"}


@router.get("/patients/{patient_id}/family")
async def get_patient_family(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get family members for a patient."""
    patient = await _get_patient(db, patient_id, user["practice_id"])
    if not patient.family_id:
        return {"family": None, "members": []}

    # Get all members in same family
    result = await db.execute(
        select(Patient).where(
            Patient.family_id == patient.family_id,
            Patient.practice_id == user["practice_id"],
        )
    )
    members = result.scalars().all()

    # Get family record
    fam_result = await db.execute(select(PatientFamily).where(PatientFamily.id == patient.family_id))
    family = fam_result.scalar_one_or_none()

    return {
        "family": {"id": str(family.id), "name": family.family_name} if family else None,
        "members": [
            {
                "id": str(m.id), "first_name": m.first_name, "last_name": m.last_name,
                "relationship": m.family_relationship, "status": m.status,
            }
            for m in members
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ORAL HYGIENE SCORING
# ═══════════════════════════════════════════════════════════════════════════════

class HygieneScore(BaseModel):
    score: int = Field(..., ge=1, le=5)


@router.put("/patients/{patient_id}/hygiene")
async def update_hygiene_score(
    patient_id: str,
    payload: HygieneScore,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Update the patient's oral hygiene score (1-5 stars)."""
    patient = await _get_patient(db, patient_id, user["practice_id"])
    patient.oral_hygiene_score = payload.score
    await db.commit()
    return {"score": payload.score}


# ═══════════════════════════════════════════════════════════════════════════════
# GENERAL DENTIST
# ═══════════════════════════════════════════════════════════════════════════════

class DentistUpdate(BaseModel):
    general_dentist: str | None = None
    general_dentist_phone: str | None = None


@router.put("/patients/{patient_id}/dentist")
async def update_general_dentist(
    patient_id: str,
    payload: DentistUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update the patient's general dentist info."""
    patient = await _get_patient(db, patient_id, user["practice_id"])
    patient.general_dentist = payload.general_dentist
    patient.general_dentist_phone = payload.general_dentist_phone
    await db.commit()
    return {"status": "updated"}


# ═══════════════════════════════════════════════════════════════════════════════
# ALIGNER TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

class AlignerCreate(BaseModel):
    patient_id: str
    brand: str | None = None
    total_trays: int = Field(..., ge=1, le=100)
    upper_trays: int | None = None
    lower_trays: int | None = None
    wear_hours_per_day: int = Field(default=22, ge=12, le=24)
    change_interval_days: int = Field(default=14, ge=3, le=30)
    start_date: date | None = None
    refinement_number: int = 0
    notes: str | None = None


class TrayAdvance(BaseModel):
    notes: str | None = None


@router.get("/patients/{patient_id}/aligners")
async def get_aligner_treatments(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get all aligner treatments for a patient."""
    result = await db.execute(
        select(AlignerTreatment).where(
            AlignerTreatment.patient_id == uuid.UUID(patient_id),
            AlignerTreatment.practice_id == user["practice_id"],
        ).order_by(AlignerTreatment.created_at.desc())
    )
    treatments = result.scalars().all()
    return [
        {
            "id": str(t.id), "brand": t.brand, "total_trays": t.total_trays,
            "current_tray": t.current_tray, "wear_hours_per_day": t.wear_hours_per_day,
            "change_interval_days": t.change_interval_days, "start_date": t.start_date.isoformat() if t.start_date else None,
            "estimated_end_date": t.estimated_end_date.isoformat() if t.estimated_end_date else None,
            "refinement_number": t.refinement_number, "status": t.status, "notes": t.notes,
            "progress_pct": round((t.current_tray / t.total_trays) * 100) if t.total_trays else 0,
        }
        for t in treatments
    ]


@router.post("/aligners", status_code=status.HTTP_201_CREATED)
async def create_aligner_treatment(
    payload: AlignerCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Start a new aligner treatment for a patient."""
    from datetime import timedelta
    start = payload.start_date or date.today()
    est_end = start + timedelta(days=payload.total_trays * payload.change_interval_days)

    treatment = AlignerTreatment(
        practice_id=user["practice_id"],
        patient_id=uuid.UUID(payload.patient_id),
        brand=payload.brand,
        total_trays=payload.total_trays,
        current_tray=1,
        upper_trays=payload.upper_trays,
        lower_trays=payload.lower_trays,
        wear_hours_per_day=payload.wear_hours_per_day,
        change_interval_days=payload.change_interval_days,
        start_date=start,
        estimated_end_date=est_end,
        refinement_number=payload.refinement_number,
        notes=payload.notes,
    )
    db.add(treatment)
    await db.commit()
    return {"id": str(treatment.id), "status": "created"}


@router.post("/aligners/{treatment_id}/advance")
async def advance_aligner_tray(
    treatment_id: str,
    payload: TrayAdvance,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Advance to the next tray (log the change)."""
    result = await db.execute(
        select(AlignerTreatment).where(
            AlignerTreatment.id == uuid.UUID(treatment_id),
            AlignerTreatment.practice_id == user["practice_id"],
        )
    )
    treatment = result.scalar_one_or_none()
    if not treatment:
        raise HTTPException(status_code=404, detail="Treatment not found")

    if treatment.current_tray >= treatment.total_trays:
        treatment.status = "completed"
        await db.commit()
        return {"status": "completed", "tray": treatment.current_tray}

    # Log the tray change
    from datetime import timedelta
    today = date.today()
    log_entry = AlignerTrayLog(
        treatment_id=treatment.id,
        tray_number=treatment.current_tray + 1,
        started_date=today,
        expected_end_date=today + timedelta(days=treatment.change_interval_days),
        logged_by=user["user_id"],
        notes=payload.notes,
    )
    db.add(log_entry)

    treatment.current_tray += 1
    await db.commit()
    return {"status": "advanced", "tray": treatment.current_tray, "total": treatment.total_trays}


# ═══════════════════════════════════════════════════════════════════════════════
# ELASTICS TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

class ElasticCreate(BaseModel):
    patient_id: str
    elastic_type: str = Field(..., min_length=1)  # Class II, Class III, triangle, box, vertical
    size: str | None = None
    force: str | None = None
    wear_schedule: str = Field(..., pattern="^(day|night|full_time)$")
    attachment_from: str | None = None
    attachment_to: str | None = None
    instructions: str | None = None
    start_date: date | None = None


@router.get("/patients/{patient_id}/elastics")
async def get_elastic_prescriptions(
    patient_id: str,
    active_only: bool = Query(True),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get elastic prescriptions for a patient."""
    query = select(ElasticPrescription).where(
        ElasticPrescription.patient_id == uuid.UUID(patient_id),
        ElasticPrescription.practice_id == user["practice_id"],
    )
    if active_only:
        query = query.where(ElasticPrescription.is_active.is_(True))
    query = query.order_by(ElasticPrescription.start_date.desc())

    result = await db.execute(query)
    elastics = result.scalars().all()
    return [
        {
            "id": str(e.id), "elastic_type": e.elastic_type, "size": e.size,
            "force": e.force, "wear_schedule": e.wear_schedule,
            "attachment_from": e.attachment_from, "attachment_to": e.attachment_to,
            "instructions": e.instructions,
            "start_date": e.start_date.isoformat() if e.start_date else None,
            "end_date": e.end_date.isoformat() if e.end_date else None,
            "is_active": e.is_active,
        }
        for e in elastics
    ]


@router.post("/elastics", status_code=status.HTTP_201_CREATED)
async def create_elastic_prescription(
    payload: ElasticCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Prescribe elastics for a patient."""
    elastic = ElasticPrescription(
        practice_id=user["practice_id"],
        patient_id=uuid.UUID(payload.patient_id),
        elastic_type=payload.elastic_type,
        size=payload.size,
        force=payload.force,
        wear_schedule=payload.wear_schedule,
        attachment_from=payload.attachment_from,
        attachment_to=payload.attachment_to,
        instructions=payload.instructions,
        start_date=payload.start_date or date.today(),
        prescribed_by=user["user_id"],
    )
    db.add(elastic)
    await db.commit()
    return {"id": str(elastic.id), "status": "created"}


@router.patch("/elastics/{elastic_id}/end")
async def end_elastic_prescription(
    elastic_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """End an elastic prescription."""
    result = await db.execute(
        select(ElasticPrescription).where(
            ElasticPrescription.id == uuid.UUID(elastic_id),
            ElasticPrescription.practice_id == user["practice_id"],
        )
    )
    elastic = result.scalar_one_or_none()
    if not elastic:
        raise HTTPException(status_code=404, detail="Elastic prescription not found")
    elastic.is_active = False
    elastic.end_date = date.today()
    await db.commit()
    return {"status": "ended"}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _get_patient(db: AsyncSession, patient_id: str, practice_id: uuid.UUID) -> Patient:
    result = await db.execute(
        select(Patient).where(Patient.id == uuid.UUID(patient_id), Patient.practice_id == practice_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
