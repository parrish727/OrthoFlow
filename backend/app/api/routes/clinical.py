"""OrthoFlow API — Phase 1 Clinical Routes.

Endpoints for patients, scheduling, appointments, chairs, DAs, treatment notes, and tooth charts.
All endpoints are practice-scoped via JWT.
"""
from uuid import UUID
from datetime import date, time, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.clinical import (
    Patient, Chair, DentalAssistant, Appointment, TreatmentNote, ToothChart,
    PatientStatus, TreatmentPhase, AppointmentStatus,
)
from app.models.models import User

router = APIRouter(prefix="/api/v1", tags=["clinical"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: str | None = None
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = None
    email: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    address: str | None = None
    responsible_party: str | None = None
    treatment_phase: TreatmentPhase = TreatmentPhase.consultation
    referring_doctor: str | None = None
    notes: str | None = None


class PatientUpdate(BaseModel):
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    email: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    address: str | None = None
    responsible_party: str | None = None
    status: PatientStatus | None = None
    treatment_phase: TreatmentPhase | None = None
    referring_doctor: str | None = None
    notes: str | None = None


class ChairCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str | None = None
    sort_order: int = 0


class DACreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    color: str | None = None
    user_id: UUID | None = None


class AppointmentCreate(BaseModel):
    patient_id: UUID
    chair_id: UUID | None = None
    da_id: UUID | None = None
    appointment_date: date
    start_time: time
    end_time: time
    duration_minutes: int = 30
    appointment_type: str | None = None
    procedure_codes: str | None = None
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    chair_id: UUID | None = None
    da_id: UUID | None = None
    appointment_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    status: AppointmentStatus | None = None
    appointment_type: str | None = None
    notes: str | None = None


class NoteCreate(BaseModel):
    patient_id: UUID
    appointment_id: UUID | None = None
    note_text: str = Field(..., min_length=1)
    note_type: str = "clinical"
    author_user_id: UUID | None = None  # optional: attribute the note to a chosen staff member


class NoteUpdate(BaseModel):
    note_text: str = Field(..., min_length=1)


class ToothChartUpdate(BaseModel):
    teeth_data: dict | None = None
    upper_wire: str | None = None
    lower_wire: str | None = None
    upper_wire_date: date | None = None
    lower_wire_date: date | None = None
    appliances: list | None = None


# ── Patients ──────────────────────────────────────────────────────────────────

@router.get("/patients")
async def list_patients(
    status: PatientStatus | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List patients for the practice with optional filtering."""
    practice_id = user["practice_id"]
    q = select(Patient).where(Patient.practice_id == practice_id)

    if status:
        q = q.where(Patient.status == status)
    if search:
        q = q.where(
            (Patient.first_name.ilike(f"%{search}%")) |
            (Patient.last_name.ilike(f"%{search}%")) |
            (Patient.email.ilike(f"%{search}%")) |
            (Patient.phone.ilike(f"%{search}%"))
        )

    q = q.order_by(Patient.last_name, Patient.first_name)
    q = q.offset((page - 1) * size).limit(size)

    result = await db.execute(q)
    patients = result.scalars().all()

    # Count total
    count_q = select(func.count(Patient.id)).where(Patient.practice_id == practice_id)
    if status:
        count_q = count_q.where(Patient.status == status)
    total = (await db.execute(count_q)).scalar()

    return {"patients": [_patient_dict(p) for p in patients], "total": total, "page": page, "size": size}


@router.post("/patients", status_code=201)
async def create_patient(
    body: PatientCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new patient record."""
    patient = Patient(practice_id=user["practice_id"], **body.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    await audit_log(db, user["practice_id"], user["user_id"], "patient.create", "patient", str(patient.id))
    return _patient_dict(patient)


@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a single patient by ID."""
    patient = await _get_patient(db, patient_id, user["practice_id"])
    await audit_log(db, user["practice_id"], user["user_id"], "patient.view", "patient", str(patient_id))
    return _patient_dict(patient)


@router.patch("/patients/{patient_id}")
async def update_patient(
    patient_id: UUID,
    body: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update patient fields."""
    patient = await _get_patient(db, patient_id, user["practice_id"])
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    patient.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(patient)
    await audit_log(db, user["practice_id"], user["user_id"], "patient.update", "patient", str(patient_id))
    return _patient_dict(patient)


@router.delete("/patients/{patient_id}", status_code=204)
async def delete_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete a patient and all related records."""
    from sqlalchemy import delete as sql_delete
    patient = await _get_patient(db, patient_id, user["practice_id"])
    # Delete related records in FK order
    for table_name in [
        "patient_visit_status", "appointments", "treatment_notes",
        "portal_messages", "portal_accounts", "hygiene_recalls",
        "insurance_subscribers", "patient_ledger_entries",
    ]:
        try:
            await db.execute(text(f"DELETE FROM {table_name} WHERE patient_id = :pid"), {"pid": patient_id})
        except Exception:
            pass  # Table may not exist
    await db.delete(patient)
    await db.commit()
    await audit_log(db, user["practice_id"], user["user_id"], "patient.delete", "patient", str(patient_id))


# ── Chairs ────────────────────────────────────────────────────────────────────

@router.get("/chairs")
async def list_chairs(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """List all chairs for the practice."""
    result = await db.execute(
        select(Chair).where(Chair.practice_id == user["practice_id"]).order_by(Chair.sort_order)
    )
    return {"chairs": [_chair_dict(c) for c in result.scalars().all()]}


@router.post("/chairs", status_code=201)
async def create_chair(body: ChairCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """Add a new chair/operatory."""
    chair = Chair(practice_id=user["practice_id"], **body.model_dump())
    db.add(chair)
    await db.commit()
    await db.refresh(chair)
    return _chair_dict(chair)


@router.delete("/chairs/{chair_id}")
async def delete_chair(chair_id: UUID, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """Deactivate a chair."""
    result = await db.execute(select(Chair).where(Chair.id == chair_id, Chair.practice_id == user["practice_id"]))
    chair = result.scalar_one_or_none()
    if not chair:
        raise HTTPException(404, "Chair not found")
    chair.is_active = False
    await db.commit()
    return {"status": "deactivated"}


# ── Dental Assistants ─────────────────────────────────────────────────────────

@router.get("/dental-assistants")
async def list_das(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """List all dental assistants for the practice."""
    result = await db.execute(
        select(DentalAssistant).where(
            DentalAssistant.practice_id == user["practice_id"],
            DentalAssistant.is_active == True,
        )
    )
    return {"dental_assistants": [_da_dict(da) for da in result.scalars().all()]}


@router.post("/dental-assistants", status_code=201)
async def create_da(body: DACreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """Add a new dental assistant."""
    da = DentalAssistant(practice_id=user["practice_id"], **body.model_dump())
    db.add(da)
    await db.commit()
    await db.refresh(da)
    return _da_dict(da)


# ── Appointments / Schedule ───────────────────────────────────────────────────

@router.get("/schedule/month")
async def get_schedule_month(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Per-day appointment summary for a calendar month.

    Powers the Dashboard monthly calendar: for each day, the total appointments and the count
    already completed (the "OrthoFlow handled automatically" signal). Also returns a simple
    AI-suggested optimization the doctor can accept or override.
    """
    practice_id = user["practice_id"]
    rows = (await db.execute(
        select(
            Appointment.appointment_date,
            func.count(Appointment.id),
            func.count(case((Appointment.status == "completed", 1))),
        ).where(
            Appointment.practice_id == practice_id,
            func.extract("year", Appointment.appointment_date) == year,
            func.extract("month", Appointment.appointment_date) == month,
            Appointment.status != "cancelled",
        ).group_by(Appointment.appointment_date)
    )).all()

    days = {
        d.isoformat(): {"date": d.isoformat(), "total": int(total or 0), "completed": int(done or 0)}
        for d, total, done in rows
    }

    # Lightweight AI-style optimization suggestion (doctor can override; nothing auto-applied).
    counts = [v["total"] for v in days.values()]
    suggestion = None
    if counts:
        avg = sum(counts) / len(counts)
        heavy = sorted([v for v in days.values() if v["total"] >= avg * 1.5], key=lambda x: -x["total"])[:3]
        if heavy:
            suggestion = {
                "type": "load_balancing",
                "message": "Some days are heavier than your monthly average. Consider spreading a few appointments to lighter days.",
                "heavy_days": [h["date"] for h in heavy],
                "avg_per_day": round(avg, 1),
            }

    return {"year": year, "month": month, "days": days, "ai_suggestion": suggestion}


@router.get("/schedule")
async def get_schedule(
    schedule_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get the daily schedule — all appointments for a given date grouped by chair."""
    if schedule_date is None:
        schedule_date = date.today()

    practice_id = user["practice_id"]

    # Get appointments for the day
    result = await db.execute(
        select(Appointment).where(
            Appointment.practice_id == practice_id,
            Appointment.appointment_date == schedule_date,
            Appointment.status != "cancelled",
        ).order_by(Appointment.start_time)
    )
    appointments = result.scalars().all()

    # Get chairs
    chair_result = await db.execute(
        select(Chair).where(Chair.practice_id == practice_id, Chair.is_active == True).order_by(Chair.sort_order)
    )
    chairs = chair_result.scalars().all()

    # Group appointments by chair
    schedule = {}
    for chair in chairs:
        schedule[str(chair.id)] = {
            "chair": _chair_dict(chair),
            "appointments": [],
        }

    unassigned = []
    for appt in appointments:
        appt_data = await _appointment_dict(db, appt)
        if appt.chair_id and str(appt.chair_id) in schedule:
            schedule[str(appt.chair_id)]["appointments"].append(appt_data)
        else:
            unassigned.append(appt_data)

    return {
        "date": schedule_date.isoformat(),
        "columns": list(schedule.values()),
        "unassigned": unassigned,
        "total_appointments": len(appointments),
    }


@router.get("/appointments")
async def list_appointments(
    patient_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    status: AppointmentStatus | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List appointments with filters."""
    q = select(Appointment).where(Appointment.practice_id == user["practice_id"])

    if patient_id:
        q = q.where(Appointment.patient_id == patient_id)
    if start_date:
        q = q.where(Appointment.appointment_date >= start_date)
    if end_date:
        q = q.where(Appointment.appointment_date <= end_date)
    if status:
        q = q.where(Appointment.status == status)

    q = q.order_by(Appointment.appointment_date.desc(), Appointment.start_time)
    q = q.offset((page - 1) * size).limit(size)

    result = await db.execute(q)
    appointments = result.scalars().all()

    return {"appointments": [await _appointment_dict(db, a) for a in appointments]}


@router.post("/appointments", status_code=201)
async def create_appointment(
    body: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new appointment."""
    practice_id = user["practice_id"]

    # Verify patient belongs to this practice
    patient = await db.execute(select(Patient).where(Patient.id == body.patient_id, Patient.practice_id == practice_id))
    if not patient.scalar_one_or_none():
        raise HTTPException(404, "Patient not found")

    appt = Appointment(
        practice_id=practice_id,
        created_by=user["user_id"],
        **body.model_dump(),
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    await audit_log(db, practice_id, user["user_id"], "appointment.create", "appointment", str(appt.id))
    return await _appointment_dict(db, appt)


@router.patch("/appointments/{appt_id}")
async def update_appointment(
    appt_id: UUID,
    body: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update an appointment (reschedule, reassign chair/DA, change status).
    Auto-advances treatment phase when specific appointment types are completed."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appt_id, Appointment.practice_id == user["practice_id"])
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Appointment not found")

    previous_status = appt.status

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(appt, field, value)
    appt.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(appt)
    await audit_log(db, user["practice_id"], user["user_id"], "appointment.update", "appointment", str(appt_id))

    # ── Treatment Phase Auto-Advancement ──────────────────────────────────────
    phase_changed = None
    if body.status == "completed" and previous_status != "completed" and appt.appointment_type:
        phase_changed = await _check_phase_advancement(db, appt, user)

    response = await _appointment_dict(db, appt)
    if phase_changed:
        response["phase_changed"] = phase_changed
    return response


class ConfirmAppointmentRequest(BaseModel):
    via: str = "call"  # call | text | email | front_desk


@router.patch("/appointments/{appt_id}/confirm")
async def confirm_appointment(
    appt_id: UUID,
    body: ConfirmAppointmentRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Front desk confirms an appointment (after a call/text/email reminder). Sets a confirmation
    that syncs everywhere (Schedule checkmark) and mirrors the MyOrthoChart portal confirm."""
    from app.models.portal import AppointmentNotification
    result = await db.execute(
        select(Appointment).where(Appointment.id == appt_id, Appointment.practice_id == user["practice_id"])
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Appointment not found")
    already_confirmed = appt.confirmed_at is not None
    appt.confirmed_at = datetime.now(timezone.utc)
    appt.confirmed_via = body.via
    if appt.status == "scheduled":
        appt.status = "confirmed"
    appt.updated_at = datetime.now(timezone.utc)
    # Idempotent: only drop a 'confirmed' notification if one isn't already on this appointment
    # (prevents duplicate feed entries when Confirm is clicked more than once or across channels).
    if not already_confirmed:
        existing_notif = (await db.execute(
            select(AppointmentNotification.id).where(
                AppointmentNotification.appointment_id == appt.id,
                AppointmentNotification.kind == "confirmed",
                AppointmentNotification.audience == "patient",
            ).limit(1)
        )).first()
        if existing_notif is None:
            db.add(AppointmentNotification(
                practice_id=appt.practice_id, patient_id=appt.patient_id, appointment_id=appt.id,
                audience="patient", kind="confirmed",
                title="Appointment confirmed",
                body=f"Your {appt.appointment_type or 'appointment'} on {appt.appointment_date} at {str(appt.start_time)[:5]} is confirmed.",
                action_url="/portal/appointments",
            ))
    await db.commit()
    await db.refresh(appt)
    await audit_log(db, user["practice_id"], user["user_id"], "appointment.confirm", "appointment", str(appt_id))
    return {"id": str(appt.id), "status": appt.status, "confirmed_at": appt.confirmed_at.isoformat(), "confirmed_via": appt.confirmed_via}


@router.delete("/appointments/{appt_id}")
async def cancel_appointment(
    appt_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Cancel an appointment."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appt_id, Appointment.practice_id == user["practice_id"])
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Appointment not found")
    appt.status = "cancelled"
    appt.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await audit_log(db, user["practice_id"], user["user_id"], "appointment.cancel", "appointment", str(appt_id))
    return {"status": "cancelled"}


# ── Treatment Notes ───────────────────────────────────────────────────────────

@router.get("/patients/{patient_id}/notes")
async def list_notes(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List treatment notes for a patient."""
    await _get_patient(db, patient_id, user["practice_id"])  # verify ownership
    result = await db.execute(
        select(TreatmentNote).where(TreatmentNote.patient_id == patient_id).order_by(TreatmentNote.created_at.desc())
    )
    return {"notes": [_note_dict(n) for n in result.scalars().all()]}


@router.post("/notes", status_code=201)
async def create_note(
    body: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a treatment note. Stamps the author's display name, initials, and color
    (per-DA color when the author is linked to a DentalAssistant, else a deterministic
    fallback) so notes are attributable at a glance on the chart."""
    await _get_patient(db, body.patient_id, user["practice_id"])  # verify ownership

    # Idempotency guard: return the existing note if an identical one (same patient + note_text)
    # was just created (<60s) — blocks accidental double-submit (e.g. Next Visit "Save" clicked
    # twice) without preventing legitimately distinct notes.
    from datetime import timedelta as _td
    payload = body.model_dump()
    author_user_id = payload.pop("author_user_id", None)  # not a TreatmentNote column
    _recent = (await db.execute(
        select(TreatmentNote).where(
            TreatmentNote.practice_id == user["practice_id"],
            TreatmentNote.patient_id == body.patient_id,
            TreatmentNote.note_text == payload.get("note_text"),
            TreatmentNote.created_at >= datetime.now(timezone.utc) - _td(seconds=60),
        ).limit(1)
    )).scalar_one_or_none()
    if _recent is not None:
        return _note_dict(_recent)

    # Author defaults to the logged-in user, but the writer may attribute the note to a chosen
    # staff member (author_user_id). author_id keeps the actual logged-in user for audit.
    resolved_author_id = author_user_id or user["user_id"]
    author_name, author_initials, author_color = await _resolve_author(db, resolved_author_id)

    note = TreatmentNote(
        practice_id=user["practice_id"],
        author_id=resolved_author_id,
        author_name=author_name,
        author_initials=author_initials,
        author_color=author_color,
        **payload,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    await audit_log(db, user["practice_id"], user["user_id"], "note.create", "treatment_note", str(note.id))
    return _note_dict(note)


@router.patch("/notes/{note_id}")
async def update_note(
    note_id: UUID,
    body: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Edit a treatment note within the edit window (NOTE_EDIT_WINDOW_HOURS after creation).

    Only the original author may edit, and only while the note is still inside the window.
    After the window closes the note is locked for integrity (an addendum would be a new note).
    """
    note = (await db.execute(
        select(TreatmentNote).where(
            TreatmentNote.id == note_id,
            TreatmentNote.practice_id == user["practice_id"],
        )
    )).scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")
    if str(note.author_id) != str(user["user_id"]):
        raise HTTPException(403, "Only the original author can edit this note.")
    if not _note_is_editable(note):
        raise HTTPException(
            409,
            f"This note is locked — notes are editable for {NOTE_EDIT_WINDOW_HOURS}h after creation. "
            "Add a new note as an addendum.",
        )

    note.note_text = body.note_text
    await db.commit()
    await db.refresh(note)
    await audit_log(db, user["practice_id"], user["user_id"], "note.update", "treatment_note", str(note.id))
    return _note_dict(note)


# ── Tooth Chart ───────────────────────────────────────────────────────────────

@router.get("/patients/{patient_id}/tooth-chart")
async def get_tooth_chart(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get the patient's tooth chart state."""
    await _get_patient(db, patient_id, user["practice_id"])

    result = await db.execute(select(ToothChart).where(ToothChart.patient_id == patient_id))
    chart = result.scalar_one_or_none()

    if not chart:
        # Return empty chart structure
        return {"patient_id": str(patient_id), "teeth_data": {}, "upper_wire": None, "lower_wire": None, "appliances": []}

    return _chart_dict(chart)


@router.put("/patients/{patient_id}/tooth-chart")
async def update_tooth_chart(
    patient_id: UUID,
    body: ToothChartUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update the patient's tooth chart (create if doesn't exist)."""
    await _get_patient(db, patient_id, user["practice_id"])

    result = await db.execute(select(ToothChart).where(ToothChart.patient_id == patient_id))
    chart = result.scalar_one_or_none()

    if not chart:
        chart = ToothChart(practice_id=user["practice_id"], patient_id=patient_id)
        db.add(chart)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(chart, field, value)
    chart.updated_at = datetime.now(timezone.utc)
    chart.updated_by = user["user_id"]
    await db.commit()
    await db.refresh(chart)
    await audit_log(db, user["practice_id"], user["user_id"], "tooth_chart.update", "tooth_chart", str(chart.id))
    return _chart_dict(chart)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_patient(db: AsyncSession, patient_id: UUID, practice_id: str) -> Patient:
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.practice_id == practice_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")
    return patient


def _patient_dict(p: Patient) -> dict:
    return {
        "id": str(p.id),
        "first_name": p.first_name,
        "middle_name": p.middle_name,
        "last_name": p.last_name,
        "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
        "gender": p.gender,
        "email": p.email,
        "phone": p.phone,
        "address": p.address,
        "responsible_party": p.responsible_party,
        "status": p.status if p.status else None,
        "treatment_phase": p.treatment_phase if p.treatment_phase else None,
        "referring_doctor": p.referring_doctor,
        "notes": p.notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _chair_dict(c: Chair) -> dict:
    return {"id": str(c.id), "name": c.name, "color": c.color, "is_active": c.is_active, "sort_order": c.sort_order}


def _da_dict(da: DentalAssistant) -> dict:
    return {"id": str(da.id), "first_name": da.first_name, "last_name": da.last_name, "color": da.color}


async def _appointment_dict(db: AsyncSession, a: Appointment) -> dict:
    # Fetch patient name
    patient_result = await db.execute(select(Patient.first_name, Patient.last_name).where(Patient.id == a.patient_id))
    patient_row = patient_result.one_or_none()
    patient_name = f"{patient_row[0]} {patient_row[1]}" if patient_row else "Unknown"

    # Fetch visit status (flow board position)
    from app.models.workflow import PatientVisitStatus
    visit_result = await db.execute(
        select(PatientVisitStatus.status).where(PatientVisitStatus.appointment_id == a.id)
    )
    visit_row = visit_result.scalar_one_or_none()
    visit_status = visit_row if visit_row else None

    # ── Payer type (Medicaid → "MC" + purple) ──────────────────────────────────
    from app.models.finance import InsuranceSubscriber, PatientLedgerEntry
    sub = (await db.execute(
        select(InsuranceSubscriber).where(
            InsuranceSubscriber.patient_id == a.patient_id,
            InsuranceSubscriber.coverage_type == "primary",
        ).limit(1)
    )).scalar_one_or_none()
    is_medicaid = bool(sub) and (sub.plan_type or "").lower() == "medicaid"
    is_consult = "consult" in (a.appointment_type or "").lower()

    # ── Owes money / late-on-payment indicator ($) ─────────────────────────────
    balance = (await db.execute(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.patient_id == a.patient_id,
            PatientLedgerEntry.practice_id == a.practice_id,
        )
    )).scalar() or 0
    owes_money = float(balance) > 0
    # "Late" heuristic: owes money AND the oldest outstanding charge is >30 days old.
    is_late = False
    if owes_money:
        oldest_charge = (await db.execute(
            select(func.min(PatientLedgerEntry.posted_date)).where(
                PatientLedgerEntry.patient_id == a.patient_id,
                PatientLedgerEntry.practice_id == a.practice_id,
                PatientLedgerEntry.entry_type == "charge",
            )
        )).scalar()
        if oldest_charge and (date.today() - oldest_charge).days > 30:
            is_late = True

    return {
        "id": str(a.id),
        "patient_id": str(a.patient_id),
        "patient_name": patient_name,
        "chair_id": str(a.chair_id) if a.chair_id else None,
        "da_id": str(a.da_id) if a.da_id else None,
        "appointment_date": a.appointment_date.isoformat(),
        "start_time": a.start_time.isoformat(),
        "end_time": a.end_time.isoformat(),
        "duration_minutes": a.duration_minutes,
        "status": a.status,
        "visit_status": visit_status,
        "confirmed_at": a.confirmed_at.isoformat() if a.confirmed_at else None,
        "confirmed_via": a.confirmed_via,
        "appointment_type": a.appointment_type,
        "notes": a.notes,
        # Precognitive schedule indicators
        "is_medicaid": is_medicaid,
        "payer_badge": "MC" if is_medicaid else None,
        "owes_money": owes_money,
        "is_late": is_late,
        "balance": round(float(balance), 2),
        "is_consult": is_consult,
    }


NOTE_EDIT_WINDOW_HOURS = 24

# Deterministic fallback palette for authors not linked to a DentalAssistant (stable per user).
_AUTHOR_FALLBACK_COLORS = [
    "#0ea5e9", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981",
    "#ef4444", "#6366f1", "#14b8a6", "#f97316", "#84cc16",
]


def _initials_from_name(name: str | None) -> str | None:
    if not name:
        return None
    parts = [p for p in name.replace(".", " ").split() if p]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


async def _resolve_author(db: AsyncSession, user_id) -> tuple[str | None, str | None, str | None]:
    """Resolve (name, initials, color) for a note author from the User record and, when the
    author is a linked DentalAssistant, that DA's chosen color. Falls back to a stable color."""
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    name = u.full_name if u else None
    initials = _initials_from_name(name)
    da = (await db.execute(
        select(DentalAssistant).where(DentalAssistant.user_id == user_id).limit(1)
    )).scalar_one_or_none()
    color = (da.color if (da and da.color) else None)
    if not color:
        color = _AUTHOR_FALLBACK_COLORS[hash(str(user_id)) % len(_AUTHOR_FALLBACK_COLORS)]
    return name, initials, color


def _note_is_editable(n: TreatmentNote) -> bool:
    if not n.created_at:
        return False
    created = n.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600.0
    return age_hours <= NOTE_EDIT_WINDOW_HOURS


def _note_dict(n: TreatmentNote) -> dict:
    return {
        "id": str(n.id),
        "patient_id": str(n.patient_id),
        "appointment_id": str(n.appointment_id) if n.appointment_id else None,
        "note_text": n.note_text,
        "ai_summary": n.ai_summary,
        "note_type": n.note_type,
        "author_id": str(n.author_id) if n.author_id else None,
        "author_name": n.author_name,
        "author_initials": n.author_initials,
        "author_color": n.author_color,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        "editable": _note_is_editable(n),
    }


def _chart_dict(c: ToothChart) -> dict:
    return {
        "id": str(c.id),
        "patient_id": str(c.patient_id),
        "teeth_data": c.teeth_data or {},
        "upper_wire": c.upper_wire,
        "lower_wire": c.lower_wire,
        "upper_wire_date": c.upper_wire_date.isoformat() if c.upper_wire_date else None,
        "lower_wire_date": c.lower_wire_date.isoformat() if c.lower_wire_date else None,
        "appliances": c.appliances or [],
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


# ── Treatment Phase Auto-Advancement ─────────────────────────────────────────

# Rules: appointment_type (lowercase) → new phase (only if patient is in expected prior phase)
PHASE_ADVANCEMENT_RULES = {
    "records": {"new_phase": "records", "from_phases": ["consultation", "observation_1", "observation_2", "observation_3", "observation_4", "pending"]},
    "initial records": {"new_phase": "records", "from_phases": ["consultation", "observation_1", "observation_2", "observation_3", "observation_4", "pending"]},
    "bonding": {"new_phase": "active", "from_phases": ["records", "bonding", "pending"]},
    "deband": {"new_phase": "retention", "from_phases": ["active", "finishing"]},
    "retainer delivery": {"new_phase": "retention", "from_phases": ["active", "finishing"]},
    "final records": {"new_phase": "complete", "from_phases": ["retention"]},
    "observation": {"new_phase": "observation_1", "from_phases": ["consultation"]},
    "observation 1": {"new_phase": "observation_1", "from_phases": ["consultation"]},
    "observation 2": {"new_phase": "observation_2", "from_phases": ["observation_1"]},
    "observation 3": {"new_phase": "observation_3", "from_phases": ["observation_2"]},
    "observation 4": {"new_phase": "observation_4", "from_phases": ["observation_3"]},
}


async def _check_phase_advancement(db: AsyncSession, appt, user: dict) -> dict | None:
    """Check if a completed appointment should auto-advance the patient's treatment phase."""
    appt_type = (appt.appointment_type or "").lower().strip()

    rule = PHASE_ADVANCEMENT_RULES.get(appt_type)
    if not rule:
        return None

    # Get the patient
    patient = (await db.execute(
        select(Patient).where(Patient.id == appt.patient_id)
    )).scalar_one_or_none()
    if not patient:
        return None

    current_phase = patient.treatment_phase or ""
    new_phase = rule["new_phase"]
    valid_from = rule["from_phases"]

    # Only advance if patient is in an expected prior phase
    if current_phase not in valid_from:
        return None

    # Don't advance if already in or past the target phase
    if current_phase == new_phase:
        return None

    # Advance the phase
    previous_phase = current_phase
    patient.treatment_phase = new_phase
    patient.updated_at = datetime.now(timezone.utc)
    await db.commit()

    await audit_log(
        db, user["practice_id"], user["user_id"],
        "patient.phase_advanced",
        "patient", str(patient.id),
    )

    return {
        "patient_id": str(patient.id),
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "previous_phase": previous_phase,
        "new_phase": new_phase,
        "reason": f"Auto-advanced: {appt.appointment_type} appointment completed",
    }
