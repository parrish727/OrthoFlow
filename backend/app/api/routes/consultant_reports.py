"""OrthoFlow API — Consultant Reports Module.
Practice optimization reports for orthodontic consultants.
Tracks treatment conversion, patient compliance, and financial health.
"""
import uuid
from datetime import date, datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.clinical import Patient, Appointment

router = APIRouter(prefix="/api/v1/reports/consultant", tags=["consultant-reports"])


@router.get("/treatment-starts")
async def treatment_starts_report(
    start_date: str = Query(None),
    end_date: str = Query(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Treatment starts (patients who moved from consultation/pending to active)."""
    practice_id = UUID(user["practice_id"])
    s_date = date.fromisoformat(start_date) if start_date else date.today() - timedelta(days=90)
    e_date = date.fromisoformat(end_date) if end_date else date.today()

    # Count patients in active treatment
    active_result = await db.execute(
        select(func.count(Patient.id)).where(
            Patient.practice_id == practice_id,
            Patient.treatment_phase.in_(["active", "active_treatment", "bonding", "finishing"]),
        )
    )
    active_count = active_result.scalar() or 0

    # Total patients
    total_result = await db.execute(
        select(func.count(Patient.id)).where(Patient.practice_id == practice_id)
    )
    total_count = total_result.scalar() or 0

    # Observation patients
    obs_result = await db.execute(
        select(func.count(Patient.id)).where(
            Patient.practice_id == practice_id,
            Patient.treatment_phase.in_(["observation_1", "observation_2", "observation_3", "observation_4"]),
        )
    )
    observation_count = obs_result.scalar() or 0

    # Pending (consulted but not started)
    pending_result = await db.execute(
        select(func.count(Patient.id)).where(
            Patient.practice_id == practice_id,
            Patient.treatment_phase.in_(["consultation", "pending", "records", "treatment_planning"]),
        )
    )
    pending_count = pending_result.scalar() or 0

    return {
        "period": {"start": s_date.isoformat(), "end": e_date.isoformat()},
        "active_treatments": active_count,
        "total_patients": total_count,
        "observation_patients": observation_count,
        "pending_patients": pending_count,
        "conversion_rate": round((active_count / total_count * 100), 1) if total_count > 0 else 0,
    }


@router.get("/missing-appointments")
async def missing_appointments_report(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Patients who missed appointments (no-shows and late cancellations)."""
    practice_id = UUID(user["practice_id"])
    thirty_days_ago = date.today() - timedelta(days=30)

    result = await db.execute(
        select(
            Patient.id, Patient.first_name, Patient.last_name,
            Appointment.appointment_date, Appointment.appointment_type
        ).join(Patient, Patient.id == Appointment.patient_id).where(
            Appointment.practice_id == practice_id,
            Appointment.status.in_(["no_show", "cancelled"]),
            Appointment.appointment_date >= thirty_days_ago,
        ).order_by(Appointment.appointment_date.desc())
    )
    rows = result.all()

    return {
        "total_missed": len(rows),
        "patients": [
            {
                "patient_id": str(r[0]),
                "patient_name": f"{r[1]} {r[2]}",
                "missed_date": r[3].isoformat() if r[3] else None,
                "appointment_type": r[4],
            }
            for r in rows
        ],
    }


@router.get("/active-no-next-appointment")
async def active_no_next_appointment(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Active treatment patients with no future appointment scheduled."""
    practice_id = UUID(user["practice_id"])
    today = date.today()

    # Get active patients
    active_patients = await db.execute(
        select(Patient.id, Patient.first_name, Patient.last_name, Patient.treatment_phase, Patient.phone).where(
            Patient.practice_id == practice_id,
            Patient.treatment_phase.in_(["active", "active_treatment", "bonding", "finishing"]),
        )
    )
    active_list = active_patients.all()

    # For each, check if they have a future appointment
    no_next = []
    for patient in active_list:
        future_appt = await db.execute(
            select(func.count(Appointment.id)).where(
                Appointment.patient_id == patient[0],
                Appointment.appointment_date >= today,
                Appointment.status.in_(["scheduled", "confirmed"]),
            )
        )
        if (future_appt.scalar() or 0) == 0:
            no_next.append({
                "patient_id": str(patient[0]),
                "patient_name": f"{patient[1]} {patient[2]}",
                "treatment_phase": patient[3],
                "phone": patient[4],
            })

    return {"total": len(no_next), "patients": no_next}


@router.get("/observation-report")
async def observation_report(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Observation patients — tracking for conversion to active treatment."""
    practice_id = UUID(user["practice_id"])

    result = await db.execute(
        select(Patient.id, Patient.first_name, Patient.last_name, Patient.treatment_phase, Patient.date_of_birth, Patient.phone).where(
            Patient.practice_id == practice_id,
            Patient.treatment_phase.in_(["observation_1", "observation_2", "observation_3", "observation_4"]),
        ).order_by(Patient.last_name)
    )
    patients = result.all()

    return {
        "total_observation": len(patients),
        "patients": [
            {
                "patient_id": str(p[0]),
                "patient_name": f"{p[1]} {p[2]}",
                "phase": p[3],
                "date_of_birth": p[4].isoformat() if p[4] else None,
                "phone": p[5],
            }
            for p in patients
        ],
    }


@router.get("/pending-no-start")
async def pending_no_start(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Patients who had consultation but haven't started treatment."""
    practice_id = UUID(user["practice_id"])

    result = await db.execute(
        select(Patient.id, Patient.first_name, Patient.last_name, Patient.phone, Patient.email, Patient.created_at).where(
            Patient.practice_id == practice_id,
            Patient.treatment_phase.in_(["consultation", "pending", "records", "treatment_planning"]),
        ).order_by(Patient.created_at.desc())
    )
    patients = result.all()

    return {
        "total_pending": len(patients),
        "patients": [
            {
                "patient_id": str(p[0]),
                "patient_name": f"{p[1]} {p[2]}",
                "phone": p[3],
                "email": p[4],
                "days_since_consult": (date.today() - p[5].date()).days if p[5] else None,
            }
            for p in patients
        ],
    }


@router.get("/overdue-payments")
async def overdue_payments(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Patients with overdue payment balances."""
    practice_id = UUID(user["practice_id"])

    # Get patients with positive balances using raw SQL for aggregation
    result = await db.execute(text("""
        SELECT p.id, p.first_name, p.last_name, p.phone,
            COALESCE(SUM(CASE WHEN le.entry_type = 'charge' THEN le.amount ELSE 0 END), 0) +
            COALESCE(SUM(CASE WHEN le.entry_type IN ('payment', 'credit') THEN le.amount ELSE 0 END), 0) as balance
        FROM patients p
        LEFT JOIN patient_ledger_entries le ON le.patient_id = p.id AND le.practice_id = p.practice_id
        WHERE p.practice_id = :practice_id
        GROUP BY p.id, p.first_name, p.last_name, p.phone
        HAVING COALESCE(SUM(CASE WHEN le.entry_type = 'charge' THEN le.amount ELSE 0 END), 0) +
               COALESCE(SUM(CASE WHEN le.entry_type IN ('payment', 'credit') THEN le.amount ELSE 0 END), 0) > 0
        ORDER BY balance DESC
    """), {"practice_id": str(practice_id)})
    rows = result.all()

    return {
        "total_overdue_patients": len(rows),
        "total_overdue_amount": sum(float(r[4]) for r in rows),
        "patients": [
            {
                "patient_id": str(r[0]),
                "patient_name": f"{r[1]} {r[2]}",
                "phone": r[3],
                "balance": float(r[4]),
            }
            for r in rows
        ],
    }


@router.get("/summary")
async def consultant_summary(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Executive summary for consultant dashboard."""
    practice_id = UUID(user["practice_id"])
    today = date.today()

    # Total patients
    total = (await db.execute(select(func.count(Patient.id)).where(Patient.practice_id == practice_id))).scalar() or 0

    # Active
    active = (await db.execute(select(func.count(Patient.id)).where(
        Patient.practice_id == practice_id,
        Patient.treatment_phase.in_(["active", "active_treatment", "bonding", "finishing"]),
    ))).scalar() or 0

    # Observation
    obs = (await db.execute(select(func.count(Patient.id)).where(
        Patient.practice_id == practice_id,
        Patient.treatment_phase.in_(["observation_1", "observation_2", "observation_3", "observation_4"]),
    ))).scalar() or 0

    # Pending
    pending = (await db.execute(select(func.count(Patient.id)).where(
        Patient.practice_id == practice_id,
        Patient.treatment_phase.in_(["consultation", "pending", "records", "treatment_planning"]),
    ))).scalar() or 0

    # Today's appointments
    today_appts = (await db.execute(select(func.count(Appointment.id)).where(
        Appointment.practice_id == practice_id,
        Appointment.appointment_date == today,
    ))).scalar() or 0

    return {
        "total_patients": total,
        "active_treatments": active,
        "observation": obs,
        "pending_starts": pending,
        "retention": total - active - obs - pending,
        "today_appointments": today_appts,
        "conversion_rate": round((active / total * 100), 1) if total > 0 else 0,
    }
