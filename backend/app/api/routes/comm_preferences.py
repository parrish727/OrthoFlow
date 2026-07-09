"""OrthoFlow API — Patient Communication Preferences & TCPA Compliance.

Manages per-patient communication preferences (channel, timing, quiet hours)
and TCPA consent tracking with immediate opt-out support.
"""
from datetime import datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.clinical import Patient
from app.models.communications import CommunicationPreference

router = APIRouter(prefix="/api/v1/communications/preferences", tags=["communication-preferences"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PreferenceUpdate(BaseModel):
    sms_enabled: bool | None = None
    email_enabled: bool | None = None
    preferred_channel: str | None = Field(None, pattern="^(sms|email)$")
    phone_number: str | None = Field(None, max_length=20)
    email_address: str | None = Field(None, max_length=255)
    reminder_24hr: bool | None = None
    reminder_2hr: bool | None = None
    recall_reminders: bool | None = None
    birthday_messages: bool | None = None
    quiet_start: time | None = None
    quiet_end: time | None = None
    language: str | None = Field(None, pattern="^[a-z]{2}$")


class ConsentRecord(BaseModel):
    consent_method: str = Field(..., min_length=1, max_length=50)
    consent_date: datetime | None = None


class PreferenceResponse(BaseModel):
    id: str
    patient_id: str
    sms_enabled: bool
    email_enabled: bool
    preferred_channel: str
    phone_number: str | None
    email_address: str | None
    reminder_24hr: bool
    reminder_2hr: bool
    recall_reminders: bool
    birthday_messages: bool
    quiet_start: time | None
    quiet_end: time | None
    tcpa_consent: bool
    tcpa_consent_date: datetime | None
    tcpa_consent_method: str | None
    tcpa_opt_out_date: datetime | None
    language: str
    updated_at: datetime


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pref_to_dict(pref: CommunicationPreference) -> dict:
    return {
        "id": str(pref.id),
        "patient_id": str(pref.patient_id),
        "sms_enabled": pref.sms_enabled,
        "email_enabled": pref.email_enabled,
        "preferred_channel": pref.preferred_channel,
        "phone_number": pref.phone_number,
        "email_address": pref.email_address,
        "reminder_24hr": pref.reminder_24hr,
        "reminder_2hr": pref.reminder_2hr,
        "recall_reminders": pref.recall_reminders,
        "birthday_messages": pref.birthday_messages,
        "quiet_start": pref.quiet_start.isoformat() if pref.quiet_start else None,
        "quiet_end": pref.quiet_end.isoformat() if pref.quiet_end else None,
        "tcpa_consent": pref.tcpa_consent,
        "tcpa_consent_date": pref.tcpa_consent_date.isoformat() if pref.tcpa_consent_date else None,
        "tcpa_consent_method": pref.tcpa_consent_method,
        "tcpa_opt_out_date": pref.tcpa_opt_out_date.isoformat() if pref.tcpa_opt_out_date else None,
        "language": pref.language,
        "updated_at": pref.updated_at.isoformat(),
    }


async def _get_or_create_prefs(
    db: AsyncSession,
    practice_id: str,
    patient_id: str,
) -> CommunicationPreference:
    """Get patient preferences, creating defaults if they don't exist."""
    result = await db.execute(
        select(CommunicationPreference).where(
            CommunicationPreference.practice_id == practice_id,
            CommunicationPreference.patient_id == patient_id,
        )
    )
    pref = result.scalar_one_or_none()
    if pref:
        return pref

    # Fetch patient info to pre-populate
    patient = (await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    pref = CommunicationPreference(
        practice_id=practice_id,
        patient_id=patient_id,
        phone_number=patient.phone,
        email_address=patient.email,
    )
    db.add(pref)
    await db.flush()
    await db.refresh(pref)
    return pref


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{patient_id}")
async def get_patient_preferences(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Get patient communication preferences. Creates defaults if not found."""
    practice_id = user["practice_id"]
    pref = await _get_or_create_prefs(db, practice_id, str(patient_id))
    await db.commit()
    return _pref_to_dict(pref)


@router.put("/{patient_id}")
async def update_patient_preferences(
    patient_id: UUID,
    body: PreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Update patient communication preferences."""
    practice_id = user["practice_id"]
    pref = await _get_or_create_prefs(db, practice_id, str(patient_id))

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pref, field, value)

    pref.updated_at = datetime.now(timezone.utc)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="communication_preference.update",
        resource_type="communication_preference",
        resource_id=str(pref.id),
        details=f"Updated fields: {', '.join(update_data.keys())}",
    )
    await db.commit()
    await db.refresh(pref)
    return _pref_to_dict(pref)


@router.post("/{patient_id}/consent", status_code=status.HTTP_201_CREATED)
async def record_tcpa_consent(
    patient_id: UUID,
    body: ConsentRecord,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Record TCPA consent for a patient (date, method)."""
    practice_id = user["practice_id"]
    pref = await _get_or_create_prefs(db, practice_id, str(patient_id))

    consent_date = body.consent_date or datetime.now(timezone.utc)
    pref.tcpa_consent = True
    pref.tcpa_consent_date = consent_date
    pref.tcpa_consent_method = body.consent_method
    pref.tcpa_opt_out_date = None  # Clear any previous opt-out
    pref.sms_enabled = True
    pref.updated_at = datetime.now(timezone.utc)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="communication_preference.tcpa_consent",
        resource_type="communication_preference",
        resource_id=str(pref.id),
        details=f"TCPA consent recorded via {body.consent_method}",
    )
    await db.commit()
    await db.refresh(pref)
    return _pref_to_dict(pref)


@router.post("/{patient_id}/opt-out")
async def tcpa_opt_out(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Immediate TCPA opt-out — disables SMS and records opt-out timestamp."""
    practice_id = user["practice_id"]
    pref = await _get_or_create_prefs(db, practice_id, str(patient_id))

    pref.sms_enabled = False
    pref.tcpa_opt_out_date = datetime.now(timezone.utc)
    pref.updated_at = datetime.now(timezone.utc)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="communication_preference.tcpa_opt_out",
        resource_type="communication_preference",
        resource_id=str(pref.id),
        details="Patient TCPA opt-out processed immediately",
    )
    await db.commit()
    await db.refresh(pref)
    return _pref_to_dict(pref)
