"""OrthoFlow API — Patient Portal.

Patient-facing endpoints with separate JWT authentication.
Patients can view appointments, message the office, fill forms, and track treatment.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.audit import audit_log
from app.core.auth import hash_password, verify_password
from app.models.portal import PortalAccount, PortalForm, PortalFormSubmission, PortalMessage
from app.models.clinical import Patient, Appointment, TreatmentNote

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/portal", tags=["patient-portal"])

portal_security = HTTPBearer()


# ── Patient Auth ──────────────────────────────────────────────────────────────


def create_patient_token(patient_id: str, practice_id: str, account_id: str) -> str:
    """Create a JWT for patient portal access."""
    payload = {
        "sub": patient_id,
        "practice_id": practice_id,
        "account_id": account_id,
        "type": "patient_portal",
        "scope": "patient",
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_patient(
    creds: HTTPAuthorizationCredentials = Depends(portal_security),
) -> dict:
    """Dependency that validates patient portal JWT tokens."""
    try:
        payload = jwt.decode(creds.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if payload.get("type") != "patient_portal":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    return {
        "patient_id": payload["sub"],
        "practice_id": payload["practice_id"],
        "account_id": payload["account_id"],
    }


# ── Schemas ───────────────────────────────────────────────────────────────────


class PatientRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    invite_token: str = Field(..., min_length=1)


class PatientLoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1)


class PatientLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    patient_id: str
    name: str


class MessageCreate(BaseModel):
    subject: str | None = Field(None, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)


class FormSubmitRequest(BaseModel):
    responses: dict = Field(..., description="Form field responses as key-value pairs")


# ── Registration & Login ──────────────────────────────────────────────────────


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_patient(
    payload: PatientRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Patient registers a portal account using an invite token."""
    # Validate invite token — find portal account with matching verification_token
    result = await db.execute(
        select(PortalAccount).where(
            PortalAccount.verification_token == payload.invite_token,
            PortalAccount.is_verified == False,  # noqa: E712
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite token",
        )

    # Check email not already taken in practice
    existing = await db.execute(
        select(PortalAccount).where(
            PortalAccount.practice_id == account.practice_id,
            PortalAccount.email == payload.email.lower().strip(),
            PortalAccount.is_verified == True,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Activate account
    account.email = payload.email.lower().strip()
    account.password_hash = hash_password(payload.password)
    account.is_verified = True
    account.verification_token = None
    account.updated_at = datetime.now(timezone.utc)

    await db.commit()

    await audit_log(
        db,
        practice_id=str(account.practice_id),
        user_id=str(account.patient_id),
        action="portal_account.register",
        resource_type="portal_account",
        resource_id=str(account.id),
    )

    logger.info("Patient portal account registered: %s", str(account.id))
    return {"message": "Account created successfully", "account_id": str(account.id)}


@router.post("/login")
async def login_patient(
    payload: PatientLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> PatientLoginResponse:
    """Patient login — returns a patient-scoped JWT."""
    result = await db.execute(
        select(PortalAccount).where(
            PortalAccount.email == payload.email.lower().strip(),
            PortalAccount.is_verified == True,  # noqa: E712
            PortalAccount.is_active == True,  # noqa: E712
        )
    )
    account = result.scalar_one_or_none()

    if not account or not verify_password(payload.password, account.password_hash):
        await audit_log(
            db,
            practice_id=str(account.practice_id) if account else "unknown",
            user_id=None,
            action="portal_account.login_failed",
            resource_type="portal_account",
            details=f"Failed login attempt for {payload.email}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Get patient name
    patient_result = await db.execute(
        select(Patient).where(Patient.id == account.patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"

    # Update last login
    account.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_patient_token(
        patient_id=str(account.patient_id),
        practice_id=str(account.practice_id),
        account_id=str(account.id),
    )

    await audit_log(
        db,
        practice_id=str(account.practice_id),
        user_id=str(account.patient_id),
        action="portal_account.login",
        resource_type="portal_account",
        resource_id=str(account.id),
    )

    return PatientLoginResponse(
        access_token=token,
        patient_id=str(account.patient_id),
        name=patient_name,
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get("/dashboard")
async def get_patient_dashboard(
    patient: dict = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Patient dashboard: upcoming appointments, treatment phase, unread messages, pending forms."""
    patient_id = patient["patient_id"]
    practice_id = patient["practice_id"]
    now = datetime.now(timezone.utc)
    today = now.date()

    # Upcoming appointments (next 5)
    appt_result = await db.execute(
        select(Appointment)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.practice_id == practice_id,
            Appointment.appointment_date >= today,
            Appointment.status.in_(["scheduled", "confirmed"]),
        )
        .order_by(Appointment.appointment_date, Appointment.start_time)
        .limit(5)
    )
    appointments = appt_result.scalars().all()

    # Treatment phase
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.practice_id == practice_id,
        )
    )
    patient_record = patient_result.scalar_one_or_none()

    # Unread messages count
    unread_result = await db.execute(
        select(func.count(PortalMessage.id)).where(
            PortalMessage.patient_id == patient_id,
            PortalMessage.practice_id == practice_id,
            PortalMessage.direction == "to_patient",
            PortalMessage.is_read == False,  # noqa: E712
        )
    )
    unread_count = unread_result.scalar() or 0

    # Pending forms
    submitted_form_ids = (
        select(PortalFormSubmission.form_id)
        .where(PortalFormSubmission.patient_id == patient_id)
    )
    pending_forms_result = await db.execute(
        select(func.count(PortalForm.id)).where(
            PortalForm.practice_id == practice_id,
            PortalForm.is_active == True,  # noqa: E712
            PortalForm.id.notin_(submitted_form_ids),
        )
    )
    pending_forms_count = pending_forms_result.scalar() or 0

    return {
        "upcoming_appointments": [
            {
                "id": str(a.id),
                "date": str(a.appointment_date),
                "start_time": str(a.start_time),
                "end_time": str(a.end_time),
                "type": a.appointment_type,
                "status": a.status,
            }
            for a in appointments
        ],
        "treatment_phase": patient_record.treatment_phase if patient_record else None,
        "unread_messages": unread_count,
        "pending_forms": pending_forms_count,
    }


# ── Appointments ──────────────────────────────────────────────────────────────


@router.get("/appointments")
async def get_patient_appointments(
    patient: dict = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
    upcoming: bool = True,
    limit: int = 20,
) -> dict:
    """Patient's appointments — upcoming or past, without internal notes."""
    patient_id = patient["patient_id"]
    practice_id = patient["practice_id"]
    today = datetime.now(timezone.utc).date()

    query = select(Appointment).where(
        Appointment.patient_id == patient_id,
        Appointment.practice_id == practice_id,
    )
    if upcoming:
        query = query.where(Appointment.appointment_date >= today)
        query = query.order_by(Appointment.appointment_date, Appointment.start_time)
    else:
        query = query.where(Appointment.appointment_date < today)
        query = query.order_by(Appointment.appointment_date.desc())

    query = query.limit(min(limit, 50))
    result = await db.execute(query)
    appointments = result.scalars().all()

    return {
        "appointments": [
            {
                "id": str(a.id),
                "date": str(a.appointment_date),
                "start_time": str(a.start_time),
                "end_time": str(a.end_time),
                "duration_minutes": a.duration_minutes,
                "type": a.appointment_type,
                "status": a.status,
            }
            for a in appointments
        ],
    }


# ── Messages ──────────────────────────────────────────────────────────────────


@router.get("/messages")
async def get_patient_messages(
    patient: dict = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Patient's message thread with the office."""
    patient_id = patient["patient_id"]
    practice_id = patient["practice_id"]

    result = await db.execute(
        select(PortalMessage)
        .where(
            PortalMessage.patient_id == patient_id,
            PortalMessage.practice_id == practice_id,
        )
        .order_by(PortalMessage.created_at.desc())
        .limit(min(limit, 100))
        .offset(offset)
    )
    messages = result.scalars().all()

    # Mark incoming messages as read
    unread_ids = [m.id for m in messages if m.direction == "to_patient" and not m.is_read]
    if unread_ids:
        for msg in messages:
            if msg.id in unread_ids:
                msg.is_read = True
                msg.read_at = datetime.now(timezone.utc)
        await db.commit()

    return {
        "messages": [
            {
                "id": str(m.id),
                "direction": m.direction,
                "subject": m.subject,
                "body": m.body,
                "is_read": m.is_read,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/messages", status_code=status.HTTP_201_CREATED)
async def send_patient_message(
    payload: MessageCreate,
    patient: dict = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Patient sends a message to the office."""
    patient_id = patient["patient_id"]
    practice_id = patient["practice_id"]

    message = PortalMessage(
        practice_id=practice_id,
        patient_id=patient_id,
        direction="from_patient",
        subject=payload.subject,
        body=payload.body,
        is_read=False,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=patient_id,
        action="portal_message.send",
        resource_type="portal_message",
        resource_id=str(message.id),
    )

    logger.info("Patient %s sent portal message %s", patient_id, str(message.id))
    return {"id": str(message.id), "created_at": message.created_at.isoformat()}


# ── Forms ─────────────────────────────────────────────────────────────────────


@router.get("/forms")
async def list_patient_forms(
    patient: dict = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List available forms for the patient (excluding already submitted)."""
    patient_id = patient["patient_id"]
    practice_id = patient["practice_id"]

    # Get IDs of forms already submitted by this patient
    submitted_form_ids = (
        select(PortalFormSubmission.form_id)
        .where(PortalFormSubmission.patient_id == patient_id)
    )

    result = await db.execute(
        select(PortalForm)
        .where(
            PortalForm.practice_id == practice_id,
            PortalForm.is_active == True,  # noqa: E712
            PortalForm.id.notin_(submitted_form_ids),
        )
        .order_by(PortalForm.name)
    )
    forms = result.scalars().all()

    return {
        "forms": [
            {
                "id": str(f.id),
                "name": f.name,
                "form_type": f.form_type,
                "description": f.description,
                "is_required_new_patient": f.is_required_new_patient,
            }
            for f in forms
        ],
    }


@router.get("/forms/{form_id}")
async def get_form_detail(
    form_id: str,
    patient: dict = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get form fields for patient to fill out."""
    practice_id = patient["practice_id"]

    result = await db.execute(
        select(PortalForm).where(
            PortalForm.id == form_id,
            PortalForm.practice_id == practice_id,
            PortalForm.is_active == True,  # noqa: E712
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")

    return {
        "id": str(form.id),
        "name": form.name,
        "form_type": form.form_type,
        "description": form.description,
        "fields": form.fields,
        "version": form.version,
    }


@router.post("/forms/{form_id}/submit", status_code=status.HTTP_201_CREATED)
async def submit_form(
    form_id: str,
    payload: FormSubmitRequest,
    patient: dict = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Patient submits form responses."""
    patient_id = patient["patient_id"]
    practice_id = patient["practice_id"]

    # Verify form exists and is active
    form_result = await db.execute(
        select(PortalForm).where(
            PortalForm.id == form_id,
            PortalForm.practice_id == practice_id,
            PortalForm.is_active == True,  # noqa: E712
        )
    )
    form = form_result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")

    # Check if already submitted
    existing = await db.execute(
        select(PortalFormSubmission).where(
            PortalFormSubmission.form_id == form_id,
            PortalFormSubmission.patient_id == patient_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Form already submitted",
        )

    submission = PortalFormSubmission(
        practice_id=practice_id,
        patient_id=patient_id,
        form_id=form_id,
        responses=payload.responses,
        status="submitted",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=patient_id,
        action="portal_form.submit",
        resource_type="portal_form_submission",
        resource_id=str(submission.id),
    )

    logger.info("Patient %s submitted form %s", patient_id, form_id)
    return {"id": str(submission.id), "status": "submitted"}


# ── Treatment Progress ────────────────────────────────────────────────────────


@router.get("/treatment-progress")
async def get_treatment_progress(
    patient: dict = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Patient's treatment phase, estimated completion, next milestone."""
    patient_id = patient["patient_id"]
    practice_id = patient["practice_id"]

    # Get patient record
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.practice_id == practice_id,
        )
    )
    patient_record = result.scalar_one_or_none()
    if not patient_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Count total and completed appointments for progress estimate
    total_appts = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.patient_id == patient_id,
            Appointment.practice_id == practice_id,
        )
    )
    total_count = total_appts.scalar() or 0

    completed_appts = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.patient_id == patient_id,
            Appointment.practice_id == practice_id,
            Appointment.status == "completed",
        )
    )
    completed_count = completed_appts.scalar() or 0

    # Next upcoming appointment
    next_appt = await db.execute(
        select(Appointment)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.practice_id == practice_id,
            Appointment.appointment_date >= datetime.now(timezone.utc).date(),
            Appointment.status.in_(["scheduled", "confirmed"]),
        )
        .order_by(Appointment.appointment_date, Appointment.start_time)
        .limit(1)
    )
    next_appointment = next_appt.scalar_one_or_none()

    # Phase progression mapping for patient-friendly display
    phase_display = {
        "consultation": {"label": "Consultation", "order": 1},
        "records": {"label": "Records & Planning", "order": 2},
        "bonding": {"label": "Bonding", "order": 3},
        "active": {"label": "Active Treatment", "order": 4},
        "finishing": {"label": "Finishing", "order": 5},
        "retention": {"label": "Retention", "order": 6},
        "complete": {"label": "Complete", "order": 7},
    }

    current_phase = patient_record.treatment_phase or "consultation"
    phase_info = phase_display.get(current_phase, {"label": current_phase, "order": 0})

    return {
        "current_phase": current_phase,
        "phase_label": phase_info["label"],
        "phase_order": phase_info["order"],
        "total_phases": 7,
        "total_appointments": total_count,
        "completed_appointments": completed_count,
        "next_appointment": {
            "date": str(next_appointment.appointment_date),
            "start_time": str(next_appointment.start_time),
            "type": next_appointment.appointment_type,
        } if next_appointment else None,
    }
