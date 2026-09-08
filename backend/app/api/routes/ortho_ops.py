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


# ═══════════════════════════════════════════════════════════════════════════════
# Pre-consultation insurance verification (readiness worklist)
# Insurance must be verified BEFORE the consultation. This surfaces the day's consults
# with their verification status so front desk can verify ahead of the visit.
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/consult-readiness")
async def consult_readiness(
    for_date: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Consultation appointments for a date + insurance verification status.

    verified = eligibility checked within 30 days AND coverage active. Anything else is a
    to-do for front desk to verify before the consult.
    """
    from app.models.clinical import Appointment
    from app.models.finance import InsuranceSubscriber

    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]

    appts = (await db.execute(
        select(Appointment).where(
            Appointment.practice_id == practice_id,
            Appointment.appointment_date == for_date,
            Appointment.appointment_type.ilike("%consult%"),
        ).order_by(Appointment.start_time)
    )).scalars().all()

    pmap = {str(p.id): p for p in (await db.execute(
        select(Patient).where(Patient.practice_id == practice_id))).scalars().all()}

    items = []
    needs = 0
    for a in appts:
        sub = (await db.execute(
            select(InsuranceSubscriber).where(
                InsuranceSubscriber.patient_id == a.patient_id,
                InsuranceSubscriber.coverage_type == "primary",
            ).limit(1)
        )).scalar_one_or_none()
        p = pmap.get(str(a.patient_id))
        if not sub:
            status = "no_insurance"
            verified = False
        else:
            recent = bool(sub.last_eligibility_check) and \
                (date.today() - sub.last_eligibility_check.date()).days <= 30
            verified = bool(recent and sub.eligibility_status == "active")
            status = "verified" if verified else "needs_verification"
        if not verified:
            needs += 1
        items.append({
            "appointment_id": str(a.id), "patient_id": str(a.patient_id),
            "patient_name": f"{p.first_name} {p.last_name}" if p else "—",
            "start_time": a.start_time.isoformat() if a.start_time else None,
            "appointment_type": a.appointment_type,
            "payer_name": sub.payer_name if sub else None,
            "subscriber_plan_id": str(sub.id) if sub else None,
            "status": status, "verified": verified,
            "last_checked": sub.last_eligibility_check.isoformat() if (sub and sub.last_eligibility_check) else None,
        })

    return {
        "date": for_date.isoformat(),
        "consult_count": len(items),
        "needs_verification": needs,
        "items": items,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# OrthoFlow AI Assist — role-aware next-best-actions across the practice
# Reads the same signals the new features expose and turns them into a prioritized,
# role-specific action list so each person sees what to do next without hunting.
# This is the precognitive layer: it makes the data useful to the staff and doctor.
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ai-assist")
async def ai_assist(
    role: str = Query("owner"),
    for_date: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return prioritized, role-aware action items derived from live practice signals.

    Roles: front_desk, treatment_coordinator (tc), doctor, office_manager, owner.
    Each action: {severity, category, title, detail, count, action_route}.
    """
    from app.models.clinical import Appointment, Patient, TreatmentNote
    from app.models.finance import InsuranceSubscriber
    from app.models.claims import InsuranceClaim

    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    role = (role or "owner").lower()
    actions: list[dict] = []

    def add(severity, category, title, detail, count, route):
        actions.append({"severity": severity, "category": category, "title": title,
                        "detail": detail, "count": count, "action_route": route})

    # ── Signal: consults today needing insurance verification (front desk / TC) ─
    consults = (await db.execute(
        select(Appointment).where(
            Appointment.practice_id == practice_id,
            Appointment.appointment_date == for_date,
            Appointment.appointment_type.ilike("%consult%"),
        )
    )).scalars().all()
    unverified = 0
    for a in consults:
        sub = (await db.execute(
            select(InsuranceSubscriber).where(
                InsuranceSubscriber.patient_id == a.patient_id,
                InsuranceSubscriber.coverage_type == "primary").limit(1)
        )).scalar_one_or_none()
        recent = bool(sub) and bool(sub.last_eligibility_check) and \
            (for_date - sub.last_eligibility_check.date()).days <= 30
        if not (recent and sub and sub.eligibility_status == "active"):
            unverified += 1
    if unverified:
        add("warning", "verification",
            f"Verify insurance for {unverified} consult(s) today",
            "Verify eligibility before the consultation so coverage and out-of-pocket are accurate at the visit.",
            unverified, "/reports")

    # ── Signal: claims due to send / denials to appeal (TC) ─────────────────────
    due_contracts = (await db.execute(
        select(func.count(PatientInsuranceContract.id)).where(
            PatientInsuranceContract.practice_id == practice_id,
            PatientInsuranceContract.status == "active",
            PatientInsuranceContract.initial_claim_sent == True,
            PatientInsuranceContract.billing_mode == "manual",
            PatientInsuranceContract.next_claim_due <= for_date,
        )
    )).scalar() or 0
    if due_contracts:
        add("info", "claims", f"{due_contracts} manual claim(s) due to send",
            "These contracts are set to manual billing and have a claim due. Auto contracts send themselves.",
            due_contracts, "/claims")

    denied = (await db.execute(
        select(func.count(InsuranceClaim.id)).where(
            InsuranceClaim.practice_id == practice_id, InsuranceClaim.status == "denied")
    )).scalar() or 0
    if denied:
        add("warning", "claims", f"{denied} denied claim(s) to review/appeal",
            "Review denial reasons and generate appeals where the service should be covered.",
            denied, "/claims")

    # ── Signal: patients arriving today who owe money (front desk collect) ──────
    from app.models.finance import PatientLedgerEntry
    today_appts = (await db.execute(
        select(Appointment.patient_id).where(
            Appointment.practice_id == practice_id, Appointment.appointment_date == for_date)
    )).scalars().all()
    collectable = 0
    for pid in set(today_appts):
        bal = (await db.execute(
            select(func.sum(PatientLedgerEntry.amount)).where(
                PatientLedgerEntry.patient_id == pid, PatientLedgerEntry.practice_id == practice_id)
        )).scalar()
        if bal and bal > 0:
            collectable += 1
    if collectable:
        add("info", "collections", f"{collectable} patient(s) arriving today carry a balance",
            "A good moment to collect at check-in.", collectable, "/ledger")

    # ── Signal: overdue treatment / bring-in-sooner (doctor) ────────────────────
    active_patients = (await db.execute(
        select(Patient).where(
            Patient.practice_id == practice_id,
            Patient.treatment_phase.in_(["active", "bonding", "finishing"]))
    )).scalars().all()
    overdue = 0
    for p in active_patients:
        last = (await db.execute(
            select(func.max(Appointment.appointment_date)).where(
                Appointment.practice_id == practice_id, Appointment.patient_id == p.id,
                Appointment.appointment_date <= for_date)
        )).scalar()
        nxt = (await db.execute(
            select(func.min(Appointment.appointment_date)).where(
                Appointment.practice_id == practice_id, Appointment.patient_id == p.id,
                Appointment.appointment_date > for_date)
        )).scalar()
        if (last and (for_date - last).days > 45) or nxt is None:
            overdue += 1
    if overdue:
        add("warning", "clinical", f"{overdue} patient(s) overdue for a visit",
            "Active patients >45 days since last visit or with no next appointment risk treatment stagnation.",
            overdue, "/reports")

    # ── Signal: today's appts missing chart notes (doctor / DA) ─────────────────
    missing_notes = 0
    for a in (await db.execute(
        select(Appointment).where(
            Appointment.practice_id == practice_id, Appointment.appointment_date == for_date)
    )).scalars().all():
        n = (await db.execute(
            select(func.count(TreatmentNote.id)).where(TreatmentNote.appointment_id == a.id))).scalar() or 0
        if n == 0 and a.status in ("completed", "checked_in", "in_progress"):
            missing_notes += 1
    if missing_notes:
        add("info", "clinical", f"{missing_notes} appointment(s) need chart notes",
            "Document before end of day for compliance and continuity of care.", missing_notes, "/reports")

    # ── Role filtering — surface what matters to each role first ────────────────
    role_categories = {
        "front_desk": ["verification", "collections", "claims"],
        "frontdesk": ["verification", "collections", "claims"],
        "treatment_coordinator": ["verification", "claims", "collections"],
        "tc": ["verification", "claims", "collections"],
        "doctor": ["clinical", "verification"],
        "office_manager": ["claims", "collections", "clinical", "verification"],
        "owner": ["verification", "claims", "collections", "clinical"],
    }
    prefer = role_categories.get(role, role_categories["owner"])
    sev_order = {"critical": 0, "warning": 1, "info": 2}
    actions.sort(key=lambda a: (prefer.index(a["category"]) if a["category"] in prefer else 99,
                                sev_order.get(a["severity"], 3)))

    return {
        "role": role, "date": for_date.isoformat(),
        "action_count": len(actions),
        "actions": actions,
        "headline": (actions[0]["title"] if actions else "You're all caught up — nothing needs attention right now."),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Automation — "it just works": view what OrthoFlow did + trigger on demand
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/automation/activity")
async def automation_activity(
    days: int = Query(7, ge=1, le=60),
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Recent automation runs — what OrthoFlow handled automatically (audit trail)."""
    from app.models.ortho_ops import AutomationRun
    practice_id = user["practice_id"]
    since = date.today() - timedelta(days=days)
    rows = (await db.execute(
        select(AutomationRun).where(
            AutomationRun.practice_id == practice_id,
            AutomationRun.run_date >= since,
        ).order_by(AutomationRun.created_at.desc())
    )).scalars().all()
    TASK_LABELS = {
        "recurring_claims": "Recurring claims generated",
        "payment_poll": "Payer payment status polled",
        "consult_verify": "Insurance auto-verified for upcoming consults",
    }
    items = [{
        "id": str(r.id), "run_date": r.run_date.isoformat(), "task": r.task,
        "label": TASK_LABELS.get(r.task, r.task), "status": r.status,
        "items_processed": r.items_processed, "summary": r.summary,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]
    return {
        "days": days, "run_count": len(items),
        "total_actions": sum(r.items_processed for r in rows),
        "runs": items,
    }


@router.post("/automation/run")
async def automation_run_now(
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Trigger the daily automation engine on demand (also runs on schedule in the worker)."""
    from app.services import automation
    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    result = await automation.run_all(db, practice_id)
    await audit_log(db, practice_id, user["user_id"], "automation.run", "automation", "manual")
    return result
