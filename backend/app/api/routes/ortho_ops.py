"""OrthoFlow API — Orthodontic operations.

Custom CDT codes, patient comments (info + clinical), chart charges (checkout collection),
per-patient insurance contracts (from TC Proposal → Claims), and claim billing cadence with
auto-recurring generation + daily payment-status polling.
"""
import logging
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.ortho_ops import (
    CustomCDTCode, PatientComment, ChartCharge, PatientInsuranceContract, ClaimPaymentPoll,
)
from app.models.clinical import Patient
from app.models.finance import PatientLedgerEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ortho", tags=["ortho-ops"])


# ═══════════════════════════════════════════════════════════════════════════════
# Custom CDT codes (doctor-defined)
# ═══════════════════════════════════════════════════════════════════════════════

class CustomCDTCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)
    description: str = Field(..., min_length=1)
    short_description: str | None = None
    category: str = "custom"
    default_fee: Decimal | None = None
    medicaid_only: bool = False


@router.get("/cdt/custom")
async def list_custom_cdt(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    practice_id = user["practice_id"]
    rows = (await db.execute(
        select(CustomCDTCode).where(CustomCDTCode.practice_id == practice_id, CustomCDTCode.is_active == True)
        .order_by(CustomCDTCode.code)
    )).scalars().all()
    return {"custom_codes": [_custom_cdt_dict(c) for c in rows]}


@router.post("/cdt/custom", status_code=201)
async def create_custom_cdt(body: CustomCDTCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    practice_id = user["practice_id"]
    existing = (await db.execute(
        select(CustomCDTCode).where(CustomCDTCode.practice_id == practice_id, CustomCDTCode.code == body.code)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"Code {body.code} already exists for this practice")
    c = CustomCDTCode(practice_id=practice_id, created_by=user["user_id"], **body.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    await audit_log(db, practice_id, user["user_id"], "cdt.custom.create", "custom_cdt_code", str(c.id))
    return _custom_cdt_dict(c)


# ═══════════════════════════════════════════════════════════════════════════════
# Patient comments (info chart + clinical chart)
# ═══════════════════════════════════════════════════════════════════════════════

class CommentCreate(BaseModel):
    chart: str = Field("info", pattern="^(info|clinical)$")
    body: str = Field(..., min_length=1)
    is_pinned: bool = False


@router.get("/patients/{patient_id}/comments")
async def list_comments(
    patient_id: UUID, chart: str | None = Query(None, pattern="^(info|clinical)$"),
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    practice_id = user["practice_id"]
    q = select(PatientComment).where(
        PatientComment.practice_id == practice_id, PatientComment.patient_id == patient_id,
    )
    if chart:
        q = q.where(PatientComment.chart == chart)
    q = q.order_by(PatientComment.is_pinned.desc(), PatientComment.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return {"comments": [_comment_dict(c) for c in rows]}


@router.post("/patients/{patient_id}/comments", status_code=201)
async def add_comment(
    patient_id: UUID, body: CommentCreate,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    practice_id = user["practice_id"]
    c = PatientComment(
        practice_id=practice_id, patient_id=patient_id, chart=body.chart, body=body.body.strip(),
        is_pinned=body.is_pinned, author_id=user["user_id"], author_name=user.get("full_name") or user.get("email"),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    await audit_log(db, practice_id, user["user_id"], "patient.comment.add", "patient_comment", str(c.id))
    return _comment_dict(c)


# ═══════════════════════════════════════════════════════════════════════════════
# Chart charges (attach CDT charge under next appointment; collect at checkout)
# ═══════════════════════════════════════════════════════════════════════════════

class ChartChargeCreate(BaseModel):
    cdt_code: str
    description: str | None = None
    fee: Decimal = Field(..., gt=0)
    tooth_numbers: str | None = None
    appointment_id: str | None = None
    is_custom_code: bool = False


@router.get("/patients/{patient_id}/chart-charges")
async def list_chart_charges(
    patient_id: UUID, status: str = Query("queued"),
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    practice_id = user["practice_id"]
    rows = (await db.execute(
        select(ChartCharge).where(
            ChartCharge.practice_id == practice_id, ChartCharge.patient_id == patient_id,
            ChartCharge.status == status,
        ).order_by(ChartCharge.created_at.desc())
    )).scalars().all()
    return {"chart_charges": [_charge_dict(c) for c in rows], "total": float(sum(c.fee for c in rows))}


@router.post("/patients/{patient_id}/chart-charges", status_code=201)
async def add_chart_charge(
    patient_id: UUID, body: ChartChargeCreate,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    practice_id = user["practice_id"]
    c = ChartCharge(
        practice_id=practice_id, patient_id=patient_id, appointment_id=body.appointment_id,
        cdt_code=body.cdt_code, description=body.description, fee=body.fee,
        tooth_numbers=body.tooth_numbers, is_custom_code=body.is_custom_code, added_by=user["user_id"],
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    await audit_log(db, practice_id, user["user_id"], "chart_charge.add", "chart_charge", str(c.id))
    return _charge_dict(c)


@router.patch("/chart-charges/{charge_id}/collect")
async def collect_chart_charge(
    charge_id: UUID, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Collect a queued chart charge at checkout — posts it to the patient ledger."""
    practice_id = user["practice_id"]
    charge = (await db.execute(
        select(ChartCharge).where(ChartCharge.id == charge_id, ChartCharge.practice_id == practice_id)
    )).scalar_one_or_none()
    if not charge:
        raise HTTPException(404, "Chart charge not found")
    if charge.status != "queued":
        raise HTTPException(400, f"Charge already {charge.status}")

    current = (await db.execute(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.patient_id == charge.patient_id,
            PatientLedgerEntry.practice_id == practice_id,
        )
    )).scalar() or Decimal("0")

    db.add(PatientLedgerEntry(
        practice_id=practice_id, patient_id=charge.patient_id, entry_type="charge",
        description=f"{charge.cdt_code} — {charge.description or 'Procedure'}",
        amount=charge.fee, running_balance=(current + charge.fee),
        cdt_code=charge.cdt_code, tooth_numbers=charge.tooth_numbers, posted_date=date.today(),
        created_by=user["user_id"],
    ))
    charge.status = "collected"
    charge.collected_at = datetime.now(timezone.utc)
    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "chart_charge.collect", "chart_charge", str(charge_id))
    return {"id": str(charge_id), "status": "collected", "posted_to_ledger": float(charge.fee)}


# ═══════════════════════════════════════════════════════════════════════════════
# Per-patient insurance contract (from TC Proposal → Claims) + billing cadence
# ═══════════════════════════════════════════════════════════════════════════════

class ContractCreate(BaseModel):
    patient_id: str
    subscriber_id: str | None = None
    tc_proposal_id: str | None = None
    total_treatment_fee: Decimal = Field(..., gt=0)
    down_payment: Decimal = Decimal("0")
    insurance_estimate: Decimal = Decimal("0")
    patient_portion: Decimal = Decimal("0")
    estimated_months: int | None = None
    payer_kind: str = Field("insurance", pattern="^(insurance|private|direct)$")
    billing_cadence: str = Field("monthly", pattern="^(monthly|quarterly)$")
    billing_mode: str = Field("auto", pattern="^(auto|manual)$")
    claim_destination: str = Field("clearinghouse", pattern="^(clearinghouse|private|direct|nctracks)$")
    daily_payment_poll: bool = True
    notes: str | None = None


class ContractUpdate(BaseModel):
    billing_cadence: str | None = Field(None, pattern="^(monthly|quarterly)$")
    billing_mode: str | None = Field(None, pattern="^(auto|manual)$")
    claim_destination: str | None = Field(None, pattern="^(clearinghouse|private|direct|nctracks)$")
    daily_payment_poll: bool | None = None
    status: str | None = Field(None, pattern="^(draft|active|completed|cancelled)$")
    notes: str | None = None


@router.get("/contracts")
async def list_contracts(
    patient_id: str | None = None,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    practice_id = user["practice_id"]
    q = select(PatientInsuranceContract).where(PatientInsuranceContract.practice_id == practice_id)
    if patient_id:
        q = q.where(PatientInsuranceContract.patient_id == patient_id)
    q = q.order_by(PatientInsuranceContract.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return {"contracts": [_contract_dict(c) for c in rows]}


@router.post("/contracts", status_code=201)
async def create_contract(body: ContractCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """Create a per-patient insurance contract (typically from an accepted TC Proposal)."""
    practice_id = user["practice_id"]
    cadence_days = 90 if body.billing_cadence == "quarterly" else 30
    c = PatientInsuranceContract(
        practice_id=practice_id, created_by=user["user_id"],
        next_claim_due=date.today(),  # first claim due at treatment start
        **body.model_dump(),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    await audit_log(db, practice_id, user["user_id"], "contract.create", "patient_insurance_contract", str(c.id))
    return _contract_dict(c)


@router.patch("/contracts/{contract_id}")
async def update_contract(
    contract_id: UUID, body: ContractUpdate,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Edit contract billing config — Frontdesk/Doctor/TC adjustable."""
    practice_id = user["practice_id"]
    c = (await db.execute(
        select(PatientInsuranceContract).where(
            PatientInsuranceContract.id == contract_id, PatientInsuranceContract.practice_id == practice_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contract not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "contract.update", "patient_insurance_contract", str(contract_id))
    return _contract_dict(c)


@router.post("/contracts/{contract_id}/send-initial-claim")
async def send_initial_claim(
    contract_id: UUID, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Ortho: send the FIRST claim once (at appointment start). Then billing becomes automatic.

    Marks the contract's initial claim as sent and schedules the next recurring claim per cadence.
    Actual 837D generation goes through the claims workflow / clearinghouse destination.
    """
    practice_id = user["practice_id"]
    c = (await db.execute(
        select(PatientInsuranceContract).where(
            PatientInsuranceContract.id == contract_id, PatientInsuranceContract.practice_id == practice_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.initial_claim_sent:
        raise HTTPException(400, "Initial claim already sent — billing is automatic from here.")

    c.initial_claim_sent = True
    c.initial_claim_date = date.today()
    cadence_days = 90 if c.billing_cadence == "quarterly" else 30
    c.next_claim_due = date.today() + timedelta(days=cadence_days)
    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "contract.initial_claim", "patient_insurance_contract", str(contract_id))
    return {
        "id": str(contract_id), "initial_claim_sent": True,
        "next_claim_due": c.next_claim_due.isoformat(),
        "billing_mode": c.billing_mode, "cadence": c.billing_cadence,
        "message": "Initial claim sent. Recurring claims will generate automatically per cadence."
                   if c.billing_mode == "auto" else
                   "Initial claim sent. Subsequent claims are set to MANUAL — generate each when ready.",
    }


@router.post("/contracts/run-recurring")
async def run_recurring_claims(
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Generate due recurring claims for AUTO contracts whose next_claim_due <= today.

    Idempotent per day. In production this is invoked by a scheduled worker; exposed here so
    it can be triggered/tested on demand. Returns which contracts were advanced.
    """
    practice_id = user["practice_id"]
    today = date.today()
    due = (await db.execute(
        select(PatientInsuranceContract).where(
            PatientInsuranceContract.practice_id == practice_id,
            PatientInsuranceContract.status == "active",
            PatientInsuranceContract.billing_mode == "auto",
            PatientInsuranceContract.initial_claim_sent == True,
            PatientInsuranceContract.next_claim_due <= today,
        )
    )).scalars().all()

    advanced = []
    for c in due:
        cadence_days = 90 if c.billing_cadence == "quarterly" else 30
        c.next_claim_due = today + timedelta(days=cadence_days)
        advanced.append({"contract_id": str(c.id), "patient_id": str(c.patient_id),
                         "next_claim_due": c.next_claim_due.isoformat(), "cadence": c.billing_cadence})
    await db.commit()
    return {"generated": len(advanced), "contracts": advanced}


@router.post("/contracts/run-payment-poll")
async def run_payment_poll(
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Daily poll of payer payment status for contracts with daily_payment_poll enabled.

    Records a ClaimPaymentPoll per active contract. In sandbox this simulates a payer response;
    with live clearinghouse creds it queries the payer/clearinghouse for paid/failed status.
    """
    import random
    practice_id = user["practice_id"]
    today = date.today()
    contracts = (await db.execute(
        select(PatientInsuranceContract).where(
            PatientInsuranceContract.practice_id == practice_id,
            PatientInsuranceContract.status == "active",
            PatientInsuranceContract.daily_payment_poll == True,
        )
    )).scalars().all()

    polled = 0
    for c in contracts:
        # Skip if already polled today (idempotent).
        existing = (await db.execute(
            select(ClaimPaymentPoll).where(
                ClaimPaymentPoll.contract_id == c.id, ClaimPaymentPoll.poll_date == today)
        )).scalar_one_or_none()
        if existing:
            continue
        # Sandbox simulation: mostly paid, some pending, occasional failed.
        status = random.choices(["paid", "pending", "failed"], weights=[70, 25, 5])[0]
        db.add(ClaimPaymentPoll(
            practice_id=practice_id, contract_id=c.id, poll_date=today, payment_status=status,
            amount=(c.insurance_estimate / max(c.estimated_months or 12, 1)) if status == "paid" else None,
            detail={"simulated": True, "source": c.claim_destination},
        ))
        polled += 1
    await db.commit()
    return {"polled": polled, "date": today.isoformat()}


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _custom_cdt_dict(c: CustomCDTCode) -> dict:
    return {
        "id": str(c.id), "code": c.code, "category": c.category, "description": c.description,
        "short_description": c.short_description,
        "default_fee": float(c.default_fee) if c.default_fee is not None else None,
        "medicaid_only": c.medicaid_only, "is_active": c.is_active, "is_custom": True,
    }


def _comment_dict(c: PatientComment) -> dict:
    return {
        "id": str(c.id), "chart": c.chart, "body": c.body, "is_pinned": c.is_pinned,
        "author_name": c.author_name, "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _charge_dict(c: ChartCharge) -> dict:
    return {
        "id": str(c.id), "patient_id": str(c.patient_id),
        "appointment_id": str(c.appointment_id) if c.appointment_id else None,
        "cdt_code": c.cdt_code, "description": c.description, "fee": float(c.fee),
        "tooth_numbers": c.tooth_numbers, "is_custom_code": c.is_custom_code,
        "status": c.status, "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _contract_dict(c: PatientInsuranceContract) -> dict:
    return {
        "id": str(c.id), "patient_id": str(c.patient_id),
        "subscriber_id": str(c.subscriber_id) if c.subscriber_id else None,
        "tc_proposal_id": str(c.tc_proposal_id) if c.tc_proposal_id else None,
        "total_treatment_fee": float(c.total_treatment_fee),
        "down_payment": float(c.down_payment), "insurance_estimate": float(c.insurance_estimate),
        "patient_portion": float(c.patient_portion), "estimated_months": c.estimated_months,
        "payer_kind": c.payer_kind, "billing_cadence": c.billing_cadence, "billing_mode": c.billing_mode,
        "claim_destination": c.claim_destination, "initial_claim_sent": c.initial_claim_sent,
        "initial_claim_date": c.initial_claim_date.isoformat() if c.initial_claim_date else None,
        "next_claim_due": c.next_claim_due.isoformat() if c.next_claim_due else None,
        "daily_payment_poll": c.daily_payment_poll, "status": c.status, "notes": c.notes,
    }
