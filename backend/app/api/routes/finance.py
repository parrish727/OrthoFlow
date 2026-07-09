"""OrthoFlow API — Patient Ledger & Insurance Plan Management.

Patient financial ledger: charges, payments, adjustments with running balance.
Insurance subscriber management: link patients to plans, track benefits.
"""
from uuid import UUID
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.finance import InsuranceSubscriber, PatientLedgerEntry
from app.models.clinical import Patient

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LedgerEntryCreate(BaseModel):
    patient_id: str
    entry_type: str = Field(..., pattern="^(charge|payment|adjustment|credit|refund)$")
    description: str = Field(..., min_length=1, max_length=500)
    amount: Decimal = Field(..., description="Positive for charges, negative for payments/credits")
    cdt_code: str | None = None
    tooth_numbers: str | None = None
    service_date: date | None = None
    payment_method: str | None = None
    reference_number: str | None = None
    claim_id: str | None = None
    notes: str | None = None


class SubscriberCreate(BaseModel):
    patient_id: str
    relationship: str = "self"
    subscriber_id: str = Field(..., min_length=1, max_length=50)
    group_number: str | None = None
    payer_id: str = Field(..., min_length=1)
    payer_name: str = Field(..., min_length=1, max_length=200)
    plan_name: str | None = None
    plan_type: str = "commercial"
    coverage_type: str = "primary"
    subscriber_first_name: str | None = None
    subscriber_last_name: str | None = None
    subscriber_dob: date | None = None
    effective_date: date | None = None
    termination_date: date | None = None
    copay_amount: Decimal | None = None
    deductible_amount: Decimal | None = None
    annual_max: Decimal | None = None
    ortho_lifetime_max: Decimal | None = None
    ortho_coverage_pct: int | None = None
    notes: str | None = None


class SubscriberUpdate(BaseModel):
    plan_name: str | None = None
    coverage_type: str | None = None
    effective_date: date | None = None
    termination_date: date | None = None
    copay_amount: Decimal | None = None
    deductible_amount: Decimal | None = None
    deductible_met: Decimal | None = None
    annual_max: Decimal | None = None
    annual_used: Decimal | None = None
    ortho_lifetime_max: Decimal | None = None
    ortho_lifetime_used: Decimal | None = None
    ortho_coverage_pct: int | None = None
    is_active: bool | None = None
    notes: str | None = None


# ── Patient Ledger ────────────────────────────────────────────────────────────

@router.get("/ledger/{patient_id}")
async def get_patient_ledger(
    patient_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    entry_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a patient's financial ledger with running balance."""
    practice_id = user["practice_id"]

    # Verify patient belongs to practice
    patient = (await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    q = select(PatientLedgerEntry).where(
        PatientLedgerEntry.practice_id == practice_id,
        PatientLedgerEntry.patient_id == patient_id,
    )
    if entry_type:
        q = q.where(PatientLedgerEntry.entry_type == entry_type)

    q = q.order_by(PatientLedgerEntry.posted_date.desc(), PatientLedgerEntry.created_at.desc())
    q = q.offset((page - 1) * size).limit(size)

    result = await db.execute(q)
    entries = result.scalars().all()

    # Get total balance
    balance_q = select(func.sum(PatientLedgerEntry.amount)).where(
        PatientLedgerEntry.practice_id == practice_id,
        PatientLedgerEntry.patient_id == patient_id,
    )
    total_balance = (await db.execute(balance_q)).scalar() or Decimal("0")

    # Count total entries
    count_q = select(func.count(PatientLedgerEntry.id)).where(
        PatientLedgerEntry.practice_id == practice_id,
        PatientLedgerEntry.patient_id == patient_id,
    )
    total = (await db.execute(count_q)).scalar()

    await audit_log(db, practice_id, user["user_id"], "ledger.view", "patient", str(patient_id))

    return {
        "patient_id": str(patient_id),
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "balance": float(total_balance),
        "total_entries": total,
        "page": page,
        "entries": [_ledger_dict(e) for e in entries],
    }


@router.post("/ledger", status_code=201)
async def create_ledger_entry(
    body: LedgerEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Post a charge, payment, or adjustment to a patient's ledger."""
    practice_id = user["practice_id"]

    # Verify patient
    patient = (await db.execute(
        select(Patient).where(Patient.id == body.patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Calculate running balance
    current_balance = (await db.execute(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.patient_id == body.patient_id,
            PatientLedgerEntry.practice_id == practice_id,
        )
    )).scalar() or Decimal("0")
    new_balance = current_balance + body.amount

    entry = PatientLedgerEntry(
        practice_id=practice_id,
        running_balance=new_balance,
        created_by=user["user_id"],
        **body.model_dump(),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    await audit_log(db, practice_id, user["user_id"], f"ledger.{body.entry_type}", "patient", body.patient_id)

    return _ledger_dict(entry)


@router.get("/ledger/{patient_id}/summary")
async def get_ledger_summary(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a patient's financial summary — total charges, payments, balance."""
    practice_id = user["practice_id"]

    charges = (await db.execute(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.patient_id == patient_id,
            PatientLedgerEntry.practice_id == practice_id,
            PatientLedgerEntry.entry_type == "charge",
        )
    )).scalar() or Decimal("0")

    payments = (await db.execute(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.patient_id == patient_id,
            PatientLedgerEntry.practice_id == practice_id,
            PatientLedgerEntry.entry_type.in_(["payment", "credit"]),
        )
    )).scalar() or Decimal("0")

    adjustments = (await db.execute(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.patient_id == patient_id,
            PatientLedgerEntry.practice_id == practice_id,
            PatientLedgerEntry.entry_type == "adjustment",
        )
    )).scalar() or Decimal("0")

    return {
        "patient_id": str(patient_id),
        "total_charges": float(charges),
        "total_payments": float(payments),
        "total_adjustments": float(adjustments),
        "balance": float(charges + payments + adjustments),
    }


# ── Insurance Subscriber Management ──────────────────────────────────────────

@router.get("/insurance/{patient_id}")
async def get_patient_insurance(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get all insurance plans for a patient."""
    practice_id = user["practice_id"]
    result = await db.execute(
        select(InsuranceSubscriber).where(
            InsuranceSubscriber.practice_id == practice_id,
            InsuranceSubscriber.patient_id == patient_id,
        ).order_by(InsuranceSubscriber.coverage_type)
    )
    subscribers = result.scalars().all()
    return {"patient_id": str(patient_id), "insurance_plans": [_subscriber_dict(s) for s in subscribers]}


@router.post("/insurance", status_code=201)
async def add_insurance_plan(
    body: SubscriberCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Add an insurance plan to a patient."""
    practice_id = user["practice_id"]

    # Verify patient
    patient = (await db.execute(
        select(Patient).where(Patient.id == body.patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    subscriber = InsuranceSubscriber(practice_id=practice_id, **body.model_dump())
    db.add(subscriber)
    await db.commit()
    await db.refresh(subscriber)

    await audit_log(db, practice_id, user["user_id"], "insurance.add", "patient", body.patient_id)
    return _subscriber_dict(subscriber)


@router.patch("/insurance/{subscriber_id}")
async def update_insurance_plan(
    subscriber_id: UUID,
    body: SubscriberUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update an insurance plan's details or benefit tracking."""
    practice_id = user["practice_id"]
    sub = (await db.execute(
        select(InsuranceSubscriber).where(
            InsuranceSubscriber.id == subscriber_id,
            InsuranceSubscriber.practice_id == practice_id,
        )
    )).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Insurance plan not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(sub, field, value)

    await db.commit()
    await db.refresh(sub)
    await audit_log(db, practice_id, user["user_id"], "insurance.update", "insurance_subscriber", str(subscriber_id))
    return _subscriber_dict(sub)


@router.delete("/insurance/{subscriber_id}")
async def remove_insurance_plan(
    subscriber_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Deactivate an insurance plan (soft delete)."""
    practice_id = user["practice_id"]
    sub = (await db.execute(
        select(InsuranceSubscriber).where(
            InsuranceSubscriber.id == subscriber_id,
            InsuranceSubscriber.practice_id == practice_id,
        )
    )).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Insurance plan not found")

    sub.is_active = False
    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "insurance.deactivate", "insurance_subscriber", str(subscriber_id))
    return {"status": "deactivated"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ledger_dict(e: PatientLedgerEntry) -> dict:
    return {
        "id": str(e.id),
        "patient_id": str(e.patient_id),
        "entry_type": e.entry_type,
        "description": e.description,
        "amount": float(e.amount),
        "running_balance": float(e.running_balance) if e.running_balance else None,
        "cdt_code": e.cdt_code,
        "tooth_numbers": e.tooth_numbers,
        "claim_id": str(e.claim_id) if e.claim_id else None,
        "service_date": e.service_date.isoformat() if e.service_date else None,
        "posted_date": e.posted_date.isoformat() if e.posted_date else None,
        "payment_method": e.payment_method,
        "reference_number": e.reference_number,
        "notes": e.notes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _subscriber_dict(s: InsuranceSubscriber) -> dict:
    return {
        "id": str(s.id),
        "patient_id": str(s.patient_id),
        "relationship": s.relationship,
        "subscriber_id": s.subscriber_id,
        "group_number": s.group_number,
        "payer_id": s.payer_id,
        "payer_name": s.payer_name,
        "plan_name": s.plan_name,
        "plan_type": s.plan_type,
        "coverage_type": s.coverage_type,
        "subscriber_first_name": s.subscriber_first_name,
        "subscriber_last_name": s.subscriber_last_name,
        "effective_date": s.effective_date.isoformat() if s.effective_date else None,
        "termination_date": s.termination_date.isoformat() if s.termination_date else None,
        "copay_amount": float(s.copay_amount) if s.copay_amount else None,
        "deductible_amount": float(s.deductible_amount) if s.deductible_amount else None,
        "deductible_met": float(s.deductible_met) if s.deductible_met else None,
        "annual_max": float(s.annual_max) if s.annual_max else None,
        "annual_used": float(s.annual_used) if s.annual_used else None,
        "ortho_lifetime_max": float(s.ortho_lifetime_max) if s.ortho_lifetime_max else None,
        "ortho_lifetime_used": float(s.ortho_lifetime_used) if s.ortho_lifetime_used else None,
        "ortho_coverage_pct": s.ortho_coverage_pct,
        "is_active": s.is_active,
        "last_eligibility_check": s.last_eligibility_check.isoformat() if s.last_eligibility_check else None,
        "eligibility_status": s.eligibility_status,
        "notes": s.notes,
    }
