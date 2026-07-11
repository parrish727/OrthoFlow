"""OrthoFlow API — Phase 1 Clinical Routes.

Endpoints for patients, scheduling, appointments, chairs, DAs, treatment notes, and tooth charts.
All endpoints are practice-scoped via JWT.
"""
from uuid import UUID
from datetime import date, time, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.clinical import (
    Patient, Chair, DentalAssistant, Appointment, TreatmentNote, ToothChart,
    PatientStatus, TreatmentPhase, AppointmentStatus,
)

router = APIRouter(prefix="/api/v1", tags=["clinical"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date | None = None
    email: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    address: str | None = None
    treatment_phase: TreatmentPhase = TreatmentPhase.consultation
    referring_doctor: str | None = None
    notes: str | None = None


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    email: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    address: str | None = None
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
            (Patient.email.ilike(f"%{search}%"))
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
    """Update an appointment (reschedule, reassign chair/DA, change status)."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appt_id, Appointment.practice_id == user["practice_id"])
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Appointment not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(appt, field, value)
    appt.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(appt)
    await audit_log(db, user["practice_id"], user["user_id"], "appointment.update", "appointment", str(appt_id))
    return await _appointment_dict(db, appt)


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
    """Create a treatment note."""
    await _get_patient(db, body.patient_id, user["practice_id"])  # verify ownership

    note = TreatmentNote(
        practice_id=user["practice_id"],
        author_id=user["user_id"],
        **body.model_dump(),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    await audit_log(db, user["practice_id"], user["user_id"], "note.create", "treatment_note", str(note.id))
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
        "last_name": p.last_name,
        "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
        "email": p.email,
        "phone": p.phone,
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
        "appointment_type": a.appointment_type,
        "notes": a.notes,
    }


def _note_dict(n: TreatmentNote) -> dict:
    return {
        "id": str(n.id),
        "patient_id": str(n.patient_id),
        "appointment_id": str(n.appointment_id) if n.appointment_id else None,
        "note_text": n.note_text,
        "ai_summary": n.ai_summary,
        "note_type": n.note_type,
        "created_at": n.created_at.isoformat() if n.created_at else None,
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
