"""OrthoFlow API — Payment Posting & ERA Processing.

Handles:
- Manual payment posting (patient payments, insurance checks)
- ERA/835 electronic remittance processing (auto-match to claims)
- Adjustment tracking
- Payment application to patient ledger
"""
from uuid import UUID
from datetime import date, datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.finance import PaymentPosting, PatientLedgerEntry, ClaimLineItem
from app.models.claims import InsuranceClaim

router = APIRouter(tags=["payment-posting"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class PaymentPostingCreate(BaseModel):
    source: str = Field("manual", pattern="^(era|manual|patient)$")
    payer_name: str | None = None
    check_number: str | None = None
    check_date: date | None = None
    total_amount: Decimal = Field(..., gt=0)
    era_trace_number: str | None = None
    notes: str | None = None


class PaymentApplication(BaseModel):
    """Apply a portion of a payment posting to a specific claim/patient."""
    claim_id: str | None = None
    patient_id: str
    amount: Decimal = Field(..., description="Amount to apply (negative = payment)")
    entry_type: str = "payment"  # payment, adjustment, refund
    description: str = Field(..., min_length=1)
    reference_number: str | None = None
    payment_method: str | None = None


class ERAImport(BaseModel):
    """Simplified ERA/835 data for import."""
    trace_number: str
    payer_name: str
    check_number: str | None = None
    check_date: date | None = None
    total_paid: Decimal
    claims: list[dict]  # [{claim_id, paid_amount, allowed_amount, patient_resp, adjustments: [{code, amount}]}]


# ── Payment Posting CRUD ──────────────────────────────────────────────────────

@router.get("/postings")
async def list_payment_postings(
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all payment postings for the practice."""
    practice_id = user["practice_id"]
    q = select(PaymentPosting).where(PaymentPosting.practice_id == practice_id)
    if status:
        q = q.where(PaymentPosting.status == status)
    q = q.order_by(PaymentPosting.created_at.desc()).offset((page - 1) * size).limit(size)

    result = await db.execute(q)
    postings = result.scalars().all()

    # Summary
    total_q = select(func.sum(PaymentPosting.total_amount)).where(PaymentPosting.practice_id == practice_id)
    unapplied_q = select(func.sum(PaymentPosting.unapplied_amount)).where(
        PaymentPosting.practice_id == practice_id, PaymentPosting.status != "complete"
    )
    total_received = (await db.execute(total_q)).scalar() or Decimal("0")
    total_unapplied = (await db.execute(unapplied_q)).scalar() or Decimal("0")

    return {
        "postings": [_posting_dict(p) for p in postings],
        "summary": {
            "total_received": float(total_received),
            "total_unapplied": float(total_unapplied),
        },
        "page": page,
    }


@router.post("/postings", status_code=201)
async def create_payment_posting(
    body: PaymentPostingCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new payment posting (manual check, patient payment, or ERA batch)."""
    practice_id = user["practice_id"]

    posting = PaymentPosting(
        practice_id=practice_id,
        source=body.source,
        payer_name=body.payer_name,
        check_number=body.check_number,
        check_date=body.check_date,
        total_amount=body.total_amount,
        unapplied_amount=body.total_amount,  # initially all unapplied
        era_trace_number=body.era_trace_number,
        notes=body.notes,
        posted_by=user["user_id"],
        status="pending",
    )
    db.add(posting)
    await db.commit()
    await db.refresh(posting)

    await audit_log(db, practice_id, user["user_id"], "payment.create", "payment_posting", str(posting.id))
    return _posting_dict(posting)


@router.get("/postings/{posting_id}")
async def get_payment_posting(
    posting_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get payment posting details with applied ledger entries."""
    practice_id = user["practice_id"]
    posting = (await db.execute(
        select(PaymentPosting).where(PaymentPosting.id == posting_id, PaymentPosting.practice_id == practice_id)
    )).scalar_one_or_none()
    if not posting:
        raise HTTPException(404, "Payment posting not found")

    # Get applied entries
    entries = (await db.execute(
        select(PatientLedgerEntry).where(PatientLedgerEntry.payment_posting_id == posting_id)
    )).scalars().all()

    result = _posting_dict(posting)
    result["applied_entries"] = [
        {
            "id": str(e.id),
            "patient_id": str(e.patient_id),
            "amount": float(e.amount),
            "description": e.description,
            "posted_date": e.posted_date.isoformat() if e.posted_date else None,
        }
        for e in entries
    ]
    return result


# ── Apply Payment to Claims/Patients ──────────────────────────────────────────

@router.post("/postings/{posting_id}/apply")
async def apply_payment(
    posting_id: UUID,
    body: PaymentApplication,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Apply a portion of a payment posting to a patient's ledger."""
    practice_id = user["practice_id"]

    posting = (await db.execute(
        select(PaymentPosting).where(PaymentPosting.id == posting_id, PaymentPosting.practice_id == practice_id)
    )).scalar_one_or_none()
    if not posting:
        raise HTTPException(404, "Payment posting not found")

    if posting.status == "complete":
        raise HTTPException(400, "Payment posting is already fully applied")

    apply_amount = abs(body.amount)
    if posting.unapplied_amount is not None and apply_amount > posting.unapplied_amount:
        raise HTTPException(400, f"Cannot apply ${apply_amount} — only ${posting.unapplied_amount} unapplied")

    # Calculate patient's new running balance
    current_balance = (await db.execute(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.patient_id == body.patient_id,
            PatientLedgerEntry.practice_id == practice_id,
        )
    )).scalar() or Decimal("0")

    ledger_amount = -apply_amount  # payments are negative in ledger
    new_balance = current_balance + ledger_amount

    # Create ledger entry
    entry = PatientLedgerEntry(
        practice_id=practice_id,
        patient_id=body.patient_id,
        entry_type=body.entry_type,
        description=body.description,
        amount=ledger_amount,
        running_balance=new_balance,
        claim_id=body.claim_id,
        payment_posting_id=posting_id,
        payment_method=body.payment_method,
        reference_number=body.reference_number or posting.check_number,
        posted_date=date.today(),
        created_by=user["user_id"],
    )
    db.add(entry)

    # Update posting amounts
    posting.applied_amount = (posting.applied_amount or Decimal("0")) + apply_amount
    posting.unapplied_amount = posting.total_amount - posting.applied_amount
    if posting.unapplied_amount <= 0:
        posting.status = "complete"
    else:
        posting.status = "partial"

    # If claim_id provided, update claim paid amount
    if body.claim_id:
        claim = (await db.execute(
            select(InsuranceClaim).where(InsuranceClaim.id == body.claim_id)
        )).scalar_one_or_none()
        if claim:
            claim.total_paid = (claim.total_paid or Decimal("0")) + apply_amount
            if claim.status == "accepted":
                claim.status = "paid"

    await db.commit()
    await db.refresh(entry)

    await audit_log(db, practice_id, user["user_id"], "payment.apply", "payment_posting", str(posting_id))

    return {
        "ledger_entry_id": str(entry.id),
        "amount_applied": float(apply_amount),
        "posting_status": posting.status,
        "posting_unapplied": float(posting.unapplied_amount) if posting.unapplied_amount else 0,
        "patient_balance": float(new_balance),
    }


# ── ERA/835 Import ────────────────────────────────────────────────────────────

@router.post("/era/import", status_code=201)
async def import_era(
    body: ERAImport,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Import ERA/835 electronic remittance — auto-creates posting and matches to claims."""
    practice_id = user["practice_id"]

    # Create the payment posting
    posting = PaymentPosting(
        practice_id=practice_id,
        source="era",
        payer_name=body.payer_name,
        check_number=body.check_number,
        check_date=body.check_date,
        total_amount=body.total_paid,
        unapplied_amount=body.total_paid,
        era_trace_number=body.trace_number,
        era_data={"claims": body.claims},
        posted_by=user["user_id"],
        status="pending",
    )
    db.add(posting)
    await db.flush()

    # Auto-match and apply to claims
    matched = 0
    for era_claim in body.claims:
        claim_id = era_claim.get("claim_id")
        if not claim_id:
            continue

        claim = (await db.execute(
            select(InsuranceClaim).where(InsuranceClaim.id == claim_id, InsuranceClaim.practice_id == practice_id)
        )).scalar_one_or_none()
        if not claim:
            continue

        paid = Decimal(str(era_claim.get("paid_amount", 0)))
        allowed = Decimal(str(era_claim.get("allowed_amount", 0)))
        patient_resp = Decimal(str(era_claim.get("patient_resp", 0)))

        # Update claim
        claim.total_paid = paid
        claim.total_allowed = allowed
        claim.patient_responsibility = patient_resp
        claim.era_reference = body.trace_number
        claim.adjudication_date = datetime.now(timezone.utc)
        if paid > 0:
            claim.status = "paid"
        else:
            claim.status = "denied"

        # Create ledger entry for the payment
        current_balance = (await db.execute(
            select(func.sum(PatientLedgerEntry.amount)).where(
                PatientLedgerEntry.patient_id == claim.patient_id,
                PatientLedgerEntry.practice_id == practice_id,
            )
        )).scalar() or Decimal("0")

        if paid > 0:
            entry = PatientLedgerEntry(
                practice_id=practice_id,
                patient_id=claim.patient_id,
                entry_type="payment",
                description=f"Insurance payment - {body.payer_name} - Check #{body.check_number or 'EFT'}",
                amount=-paid,
                running_balance=current_balance - paid,
                claim_id=claim_id,
                payment_posting_id=posting.id,
                payment_method="insurance",
                reference_number=body.trace_number,
                posted_date=date.today(),
                created_by=user["user_id"],
            )
            db.add(entry)

        # Update posting applied amount
        posting.applied_amount = (posting.applied_amount or Decimal("0")) + paid
        matched += 1

    # Update posting status
    posting.unapplied_amount = posting.total_amount - (posting.applied_amount or Decimal("0"))
    if posting.unapplied_amount <= 0:
        posting.status = "complete"
    elif matched > 0:
        posting.status = "partial"

    await db.commit()
    await db.refresh(posting)

    await audit_log(db, practice_id, user["user_id"], "era.import", "payment_posting", str(posting.id))

    return {
        "posting_id": str(posting.id),
        "trace_number": body.trace_number,
        "total_paid": float(body.total_paid),
        "claims_matched": matched,
        "claims_total": len(body.claims),
        "status": posting.status,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _posting_dict(p: PaymentPosting) -> dict:
    return {
        "id": str(p.id),
        "source": p.source,
        "payer_name": p.payer_name,
        "check_number": p.check_number,
        "check_date": p.check_date.isoformat() if p.check_date else None,
        "total_amount": float(p.total_amount),
        "applied_amount": float(p.applied_amount) if p.applied_amount else 0,
        "unapplied_amount": float(p.unapplied_amount) if p.unapplied_amount else float(p.total_amount),
        "era_trace_number": p.era_trace_number,
        "status": p.status,
        "posted_date": p.posted_date.isoformat() if p.posted_date else None,
        "notes": p.notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
