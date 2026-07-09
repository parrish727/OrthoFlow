"""OrthoFlow API — Phase 4a Imaging Alerts.

Overdue imaging detection and alert management.
Generates alerts based on treatment phase rules:
  - Active treatment: pano every 6 months, ceph every 12 months
  - Retention: pano every 12 months
  - Initial records: pano + ceph required within 30 days of starting
"""
import logging
import uuid
from datetime import date, datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.clinical import Patient
from app.models.imaging import PatientImage, ImagingAlert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/imaging/alerts", tags=["imaging-alerts"])


# ── Constants ─────────────────────────────────────────────────────────────────

# Treatment phase imaging rules: (image_type, interval_days, rule_description)
IMAGING_RULES: dict[str, list[tuple[str, int, str]]] = {
    "active": [
        ("pano", 180, "Active treatment: panoramic every 6 months"),
        ("ceph", 365, "Active treatment: cephalometric every 12 months"),
    ],
    "finishing": [
        ("pano", 180, "Finishing phase: panoramic every 6 months"),
        ("ceph", 365, "Finishing phase: cephalometric every 12 months"),
    ],
    "retention": [
        ("pano", 365, "Retention: panoramic every 12 months"),
    ],
    "records": [
        ("pano", 30, "Initial records: panoramic required within 30 days"),
        ("ceph", 30, "Initial records: cephalometric required within 30 days"),
    ],
    "bonding": [
        ("pano", 180, "Bonding phase: panoramic every 6 months"),
    ],
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: str
    patient_id: str
    image_type: str
    last_taken_date: str | None
    due_date: str
    status: str
    treatment_phase: str | None
    rule_description: str | None
    dismissed_by: str | None
    dismissed_at: str | None
    completed_image_id: str | None
    created_at: str


class DismissRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class CompleteRequest(BaseModel):
    image_id: str = Field(..., description="UUID of the image that fulfilled this alert")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _alert_to_response(alert: ImagingAlert) -> dict:
    return {
        "id": str(alert.id),
        "patient_id": str(alert.patient_id),
        "image_type": alert.image_type,
        "last_taken_date": alert.last_taken_date.isoformat() if alert.last_taken_date else None,
        "due_date": alert.due_date.isoformat(),
        "status": alert.status,
        "treatment_phase": alert.treatment_phase,
        "rule_description": alert.rule_description,
        "dismissed_by": str(alert.dismissed_by) if alert.dismissed_by else None,
        "dismissed_at": alert.dismissed_at.isoformat() if alert.dismissed_at else None,
        "completed_image_id": str(alert.completed_image_id) if alert.completed_image_id else None,
        "created_at": alert.created_at.isoformat() if alert.created_at else "",
    }


# ── List alerts ───────────────────────────────────────────────────────────────

@router.get("/")
async def list_alerts(
    status: str | None = Query(None, description="Filter by status: pending, dismissed, completed"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all overdue imaging alerts for the practice."""
    practice_id = current_user["practice_id"]

    conditions = [ImagingAlert.practice_id == practice_id]
    if status:
        if status not in ("pending", "dismissed", "completed"):
            raise HTTPException(
                status_code=400,
                detail="status must be one of: pending, dismissed, completed",
            )
        conditions.append(ImagingAlert.status == status)

    result = await db.execute(
        select(ImagingAlert)
        .where(and_(*conditions))
        .order_by(ImagingAlert.due_date.asc())
    )
    alerts = result.scalars().all()

    return {
        "alerts": [_alert_to_response(a) for a in alerts],
        "total": len(alerts),
    }


# ── Generate alerts ───────────────────────────────────────────────────────────

@router.post("/generate", status_code=200)
async def generate_alerts(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scan all active patients and generate overdue imaging alerts.

    Rules applied per treatment phase:
      - Active/Finishing: pano every 6mo, ceph every 12mo
      - Retention: pano every 12mo
      - Records/Bonding: pano + ceph within 30 days of phase start
    """
    practice_id = current_user["practice_id"]
    today = date.today()
    alerts_created = 0
    patients_scanned = 0

    # Get all active patients for this practice
    patient_result = await db.execute(
        select(Patient).where(
            Patient.practice_id == practice_id,
            Patient.status == "active",
        )
    )
    patients = patient_result.scalars().all()

    for patient in patients:
        patients_scanned += 1
        phase = patient.treatment_phase

        # Get rules for this treatment phase
        rules = IMAGING_RULES.get(phase, [])
        if not rules:
            continue

        for image_type, interval_days, rule_desc in rules:
            # Find the most recent image of this type for the patient
            latest_result = await db.execute(
                select(PatientImage.captured_date)
                .where(
                    PatientImage.practice_id == practice_id,
                    PatientImage.patient_id == patient.id,
                    PatientImage.image_type == image_type,
                    PatientImage.status == "active",
                )
                .order_by(PatientImage.captured_date.desc())
                .limit(1)
            )
            latest_date = latest_result.scalar_one_or_none()

            # Determine due date
            if latest_date:
                due_date = latest_date + timedelta(days=interval_days)
            else:
                # No image of this type ever taken — due immediately
                # Use patient creation as baseline for initial records
                due_date = (patient.created_at.date() if patient.created_at else today) + timedelta(days=interval_days)

            # Only create alert if overdue (due_date <= today)
            if due_date > today:
                continue

            # Check if a pending alert already exists for this patient + type
            existing = await db.execute(
                select(ImagingAlert.id).where(
                    ImagingAlert.practice_id == practice_id,
                    ImagingAlert.patient_id == patient.id,
                    ImagingAlert.image_type == image_type,
                    ImagingAlert.status == "pending",
                )
            )
            if existing.scalar_one_or_none():
                continue  # Don't create duplicate alerts

            # Create the alert
            alert = ImagingAlert(
                id=uuid.uuid4(),
                practice_id=practice_id,
                patient_id=patient.id,
                image_type=image_type,
                last_taken_date=latest_date,
                due_date=due_date,
                status="pending",
                treatment_phase=phase,
                rule_description=rule_desc,
            )
            db.add(alert)
            alerts_created += 1

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=current_user["user_id"],
        action="alert.generate",
        resource_type="imaging_alert",
        details=f"Scanned {patients_scanned} patients, created {alerts_created} new alerts",
    )
    await db.commit()

    logger.info("imaging_alerts_generated", extra={
        "practice_id": practice_id,
        "patients_scanned": patients_scanned,
        "alerts_created": alerts_created,
    })

    return {
        "patients_scanned": patients_scanned,
        "alerts_created": alerts_created,
    }


# ── Dismiss alert ─────────────────────────────────────────────────────────────

@router.patch("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    payload: DismissRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss an imaging alert with a reason."""
    practice_id = current_user["practice_id"]

    result = await db.execute(
        select(ImagingAlert).where(
            ImagingAlert.id == alert_id,
            ImagingAlert.practice_id == practice_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot dismiss alert with status '{alert.status}'")

    alert.status = "dismissed"
    alert.dismissed_by = current_user["user_id"]
    alert.dismissed_at = datetime.now(timezone.utc)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=current_user["user_id"],
        action="alert.dismiss",
        resource_type="imaging_alert",
        resource_id=str(alert_id),
        details=f"Dismissed: {payload.reason}",
    )
    await db.commit()

    return _alert_to_response(alert)


# ── Complete alert ────────────────────────────────────────────────────────────

@router.patch("/{alert_id}/complete")
async def complete_alert(
    alert_id: str,
    payload: CompleteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an alert as completed by linking to the fulfilling image."""
    practice_id = current_user["practice_id"]

    result = await db.execute(
        select(ImagingAlert).where(
            ImagingAlert.id == alert_id,
            ImagingAlert.practice_id == practice_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot complete alert with status '{alert.status}'")

    # Verify the linked image exists and belongs to this practice
    image_result = await db.execute(
        select(PatientImage).where(
            PatientImage.id == payload.image_id,
            PatientImage.practice_id == practice_id,
            PatientImage.status == "active",
        )
    )
    image = image_result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Linked image not found")

    alert.status = "completed"
    alert.completed_image_id = payload.image_id

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=current_user["user_id"],
        action="alert.complete",
        resource_type="imaging_alert",
        resource_id=str(alert_id),
        details=f"Completed with image {payload.image_id}",
    )
    await db.commit()

    return _alert_to_response(alert)
