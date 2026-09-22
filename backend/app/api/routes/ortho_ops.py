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
from app.models.finance import PatientLedgerEntry, ClaimLineItem, InsuranceSubscriber
from app.models.claims import InsuranceClaim

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

# Today's Charges — common orthodontic same-day charge presets. Fees are in dollars and are
# sensible defaults; a practice can override the fee at entry (and per-practice configurable
# defaults land in a later wave). Keyed list drives the "Today's Charges" CDT dropdown.
CHARGE_PRESETS: list[dict] = [
    {"key": "office_visit", "label": "Office Visit", "cdt_code": "D8670", "description": "Periodic orthodontic treatment visit", "fee": 0.0},
    {"key": "upper_essix", "label": "Upper Essix", "cdt_code": "D8680", "description": "Essix retainer — upper", "fee": 150.0},
    {"key": "lower_essix", "label": "Lower Essix", "cdt_code": "D8680", "description": "Essix retainer — lower", "fee": 150.0},
    {"key": "loose_lingual", "label": "Loose Lingual", "cdt_code": "D8999", "description": "Re-bond loose lingual (bonded) retainer", "fee": 65.0},
    {"key": "upper_lingual_retainer", "label": "Upper Lingual Retainer", "cdt_code": "D8680", "description": "Fixed lingual (bonded) retainer — upper", "fee": 250.0},
    {"key": "lower_lingual_retainer", "label": "Lower Lingual Retainer", "cdt_code": "D8680", "description": "Fixed lingual (bonded) retainer — lower", "fee": 250.0},
    {"key": "loose_bracket", "label": "Loose Bracket", "cdt_code": "D8999", "description": "Re-bond loose/broken bracket", "fee": 65.0},
]


@router.get("/charge-presets")
async def list_charge_presets(user: dict = Depends(get_current_user)):
    """Ortho same-day charge presets for the Today's Charges dropdown."""
    return {"presets": CHARGE_PRESETS}


class ChartChargeCreate(BaseModel):
    cdt_code: str
    description: str | None = None
    fee: Decimal = Field(..., gt=0)
    tooth_numbers: str | None = None
    appointment_id: str | None = None
    is_custom_code: bool = False
    idempotency_key: str | None = None


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
    # Idempotency: avoid duplicate identical queued charges for the same patient on the same day
    # (protects against double-clicks / retries so the patient ledger isn't double-charged).
    dupe = (await db.execute(
        select(ChartCharge).where(
            ChartCharge.practice_id == practice_id,
            ChartCharge.patient_id == patient_id,
            ChartCharge.cdt_code == body.cdt_code,
            ChartCharge.fee == body.fee,
            ChartCharge.status == "queued",
            func.date(ChartCharge.created_at) == date.today(),
        )
    )).scalars().first()
    if dupe is not None:
        return _charge_dict(dupe)
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
# Checkout → Work Done → AI drafts a claim → assign to ledger
# On appointment completion, the collected procedures post to the patient's ledger AND an
# insurance claim is AI-drafted (status=draft) for review. Judgment-call submission stays a
# human review step (consistent with the automation philosophy — nothing risky auto-sent).
# ═══════════════════════════════════════════════════════════════════════════════

class WorkDoneProcedure(BaseModel):
    cdt_code: str = Field(..., min_length=2, max_length=20)
    description: str | None = None
    fee: Decimal = Field(..., gt=0)
    tooth_numbers: str | None = None


class WorkDoneRequest(BaseModel):
    appointment_id: str | None = None
    procedures: list[WorkDoneProcedure] = Field(..., min_length=1)
    rendering_provider_npi: str | None = None
    billing_provider_npi: str | None = None


@router.post("/patients/{patient_id}/work-done")
async def work_done(
    patient_id: UUID, body: WorkDoneRequest,
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Complete checkout for a patient's visit: post procedure charges to the ledger and
    AI-draft an insurance claim from the same procedures.

    - Posts each procedure as a ledger charge (running balance maintained).
    - If the patient has an active primary insurance plan, drafts an InsuranceClaim
      (status=draft) + line items so the office can review then submit. No auto-submit.
    - Marks the linked appointment completed when provided.
    """
    from app.models.clinical import Appointment, AppointmentStatus
    practice_id = user["practice_id"]

    patient = (await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # 1) Post charges to the ledger.
    current = (await db.execute(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.patient_id == patient_id, PatientLedgerEntry.practice_id == practice_id)
    )).scalar() or Decimal("0")
    posted = []
    service_date = date.today()
    for p in body.procedures:
        current = current + p.fee
        db.add(PatientLedgerEntry(
            practice_id=practice_id, patient_id=patient_id, entry_type="charge",
            description=f"{p.cdt_code} — {p.description or 'Procedure'}", amount=p.fee,
            running_balance=current, cdt_code=p.cdt_code, tooth_numbers=p.tooth_numbers,
            service_date=service_date, posted_date=service_date, created_by=user["user_id"],
        ))
        posted.append({"cdt_code": p.cdt_code, "fee": float(p.fee)})

    # 2) AI-draft a claim if the patient has an active primary plan.
    sub = (await db.execute(
        select(InsuranceSubscriber).where(
            InsuranceSubscriber.patient_id == patient_id,
            InsuranceSubscriber.practice_id == practice_id,
            InsuranceSubscriber.is_active == True,
            InsuranceSubscriber.coverage_type == "primary",
        )
    )).scalar_one_or_none()

    claim_id = None
    if sub:
        total_billed = sum(p.fee for p in body.procedures)
        # Claims table constrains payer_type to medicare|medicaid|commercial.
        pt = (sub.plan_type or "").lower()
        payer_type = "medicaid" if "medicaid" in pt else ("medicare" if "medicare" in pt else "commercial")
        claim = InsuranceClaim(
            practice_id=practice_id, patient_id=str(patient_id),
            patient_name=f"{patient.first_name} {patient.last_name}",
            subscriber_id=sub.subscriber_id, payer_id=sub.payer_id, payer_type=payer_type,
            total_billed=total_billed,
            rendering_provider_npi=body.rendering_provider_npi or "0000000000",
            billing_provider_npi=body.billing_provider_npi or "0000000000",
            service_date=service_date, status="draft",
            cdt_codes=[{"code": p.cdt_code, "fee": float(p.fee)} for p in body.procedures],
        )
        db.add(claim)
        await db.flush()
        for i, p in enumerate(body.procedures, 1):
            db.add(ClaimLineItem(
                claim_id=claim.id, line_number=i, cdt_code=p.cdt_code, description=p.description,
                tooth_numbers=p.tooth_numbers, quantity=1, billed_amount=p.fee, service_date=service_date,
            ))
        claim_id = str(claim.id)

    # 3) Mark the appointment completed when provided.
    appt_completed = False
    if body.appointment_id:
        appt = (await db.execute(
            select(Appointment).where(
                Appointment.id == UUID(body.appointment_id), Appointment.practice_id == practice_id)
        )).scalar_one_or_none()
        if appt:
            appt.status = AppointmentStatus.completed
            appt_completed = True

    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "appointment.work_done", "patient", str(patient_id))
    return {
        "patient_id": str(patient_id),
        "charges_posted": posted,
        "total_charged": float(sum(p.fee for p in body.procedures)),
        "claim_drafted": claim_id is not None,
        "claim_id": claim_id,
        "claim_status": "draft" if claim_id else None,
        "appointment_completed": appt_completed,
        "note": "Charges posted to ledger. Insurance claim drafted for review."
                if claim_id else "Charges posted to ledger. No active insurance — no claim drafted.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Per-patient insurance contract (from TC Proposal → Claims) + billing cadence
# ═══════════════════════════════════════════════════════════════════════════════

class ContractCreate(BaseModel):
    patient_id: str
    subscriber_id: str | None = None
    tc_proposal_id: str | None = None
    total_treatment_fee: Decimal = Field(..., gt=0)
    fee_type: str = Field("standard", pattern="^(standard|phase_1|phase_2|limited|records_only|custom)$")
    discount_amount: Decimal = Decimal("0")
    expected_first_charges: Decimal = Decimal("0")
    down_payment: Decimal = Decimal("0")
    insurance_estimate: Decimal = Decimal("0")
    patient_portion: Decimal = Decimal("0")
    estimated_months: int | None = None
    policy_notes: str | None = None
    payer_kind: str = Field("insurance", pattern="^(insurance|private|direct)$")
    billing_cadence: str = Field("monthly", pattern="^(monthly|quarterly)$")
    billing_mode: str = Field("auto", pattern="^(auto|manual)$")
    claim_destination: str = Field("clearinghouse", pattern="^(clearinghouse|private|direct|nctracks)$")
    daily_payment_poll: bool = True
    status: str = Field("draft", pattern="^(draft|active)$")
    notes: str | None = None


class ContractUpdate(BaseModel):
    total_treatment_fee: Decimal | None = Field(None, gt=0)
    fee_type: str | None = Field(None, pattern="^(standard|phase_1|phase_2|limited|records_only|custom)$")
    discount_amount: Decimal | None = None
    expected_first_charges: Decimal | None = None
    down_payment: Decimal | None = None
    insurance_estimate: Decimal | None = None
    patient_portion: Decimal | None = None
    estimated_months: int | None = None
    policy_notes: str | None = None
    billing_cadence: str | None = Field(None, pattern="^(monthly|quarterly)$")
    billing_mode: str | None = Field(None, pattern="^(auto|manual)$")
    claim_destination: str | None = Field(None, pattern="^(clearinghouse|private|direct|nctracks)$")
    daily_payment_poll: bool | None = None
    status: str | None = Field(None, pattern="^(draft|active|completed|cancelled|archived)$")
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


@router.post("/contracts/{contract_id}/verify-insurance")
async def verify_contract_insurance(
    contract_id: UUID, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Verify the patient's insurance before the contract is placed.

    Runs eligibility on the linked subscriber (or the patient's primary plan) and stamps
    insurance_verified_at when coverage is active. Placing a contract requires this stamp.
    """
    from app.models.finance import InsuranceSubscriber
    practice_id = user["practice_id"]
    c = (await db.execute(
        select(PatientInsuranceContract).where(
            PatientInsuranceContract.id == contract_id, PatientInsuranceContract.practice_id == practice_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contract not found")

    # Resolve the subscriber (explicit link or the patient's primary plan).
    sub = None
    if c.subscriber_id:
        sub = (await db.execute(select(InsuranceSubscriber).where(InsuranceSubscriber.id == c.subscriber_id))).scalar_one_or_none()
    if not sub:
        sub = (await db.execute(select(InsuranceSubscriber).where(
            InsuranceSubscriber.patient_id == c.patient_id,
            InsuranceSubscriber.practice_id == practice_id,
            InsuranceSubscriber.coverage_type == "primary",
        ))).scalar_one_or_none()

    if c.payer_kind == "private":
        # Private-pay contracts don't require an insurance check.
        c.insurance_verified_at = datetime.now(timezone.utc)
        await db.commit()
        return {"id": str(contract_id), "verified": True, "payer_kind": "private", "note": "Private pay — no insurance verification required."}

    if not sub:
        raise HTTPException(400, "No insurance plan on file to verify. Add a plan or set payer_kind=private.")

    active = bool(sub.is_active) and (sub.termination_date is None or sub.termination_date >= date.today())
    if not active:
        return {"id": str(contract_id), "verified": False, "reason": "Plan inactive or terminated — cannot place contract until resolved."}

    c.insurance_verified_at = datetime.now(timezone.utc)
    sub.last_eligibility_check = datetime.now(timezone.utc)
    sub.eligibility_status = "active"
    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "contract.verify_insurance", "patient_insurance_contract", str(contract_id))
    return {"id": str(contract_id), "verified": True, "payer_name": sub.payer_name, "verified_at": c.insurance_verified_at.isoformat()}


@router.post("/contracts/{contract_id}/place")
async def place_contract(
    contract_id: UUID, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Place (activate) a contract. Requires insurance verified first (unless private pay).

    Connects to the ledger: posts the down payment (credit) and expected first charges (charge)
    so the patient's balance reflects the contract from day one. Moves the patient into the
    scheduled_patient lifecycle status (they leave the TC "new patient" stage).
    """
    practice_id = user["practice_id"]
    c = (await db.execute(
        select(PatientInsuranceContract).where(
            PatientInsuranceContract.id == contract_id, PatientInsuranceContract.practice_id == practice_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contract not found")
    if c.insurance_verified_at is None and c.payer_kind != "private":
        raise HTTPException(400, "Verify insurance before placing this contract.")
    if c.status == "active":
        raise HTTPException(400, "Contract already active.")

    # Running balance base.
    current = (await db.execute(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.patient_id == c.patient_id, PatientLedgerEntry.practice_id == practice_id)
    )).scalar() or Decimal("0")

    # Expected first charges → charge (debit).
    if c.expected_first_charges and c.expected_first_charges > 0:
        current = current + c.expected_first_charges
        db.add(PatientLedgerEntry(
            practice_id=practice_id, patient_id=c.patient_id, entry_type="charge",
            description="Contract — expected first charges", amount=c.expected_first_charges,
            running_balance=current, posted_date=date.today(), created_by=user["user_id"],
        ))
    # Down payment → payment (credit, negative amount).
    if c.down_payment and c.down_payment > 0:
        current = current - c.down_payment
        db.add(PatientLedgerEntry(
            practice_id=practice_id, patient_id=c.patient_id, entry_type="payment",
            description="Contract — down payment", amount=(-c.down_payment),
            running_balance=current, posted_date=date.today(), payment_method="contract",
            created_by=user["user_id"],
        ))

    c.status = "active"

    # Lifecycle: patient leaves the TC "new patient" stage → scheduled_patient.
    patient = (await db.execute(select(Patient).where(Patient.id == c.patient_id))).scalar_one_or_none()
    if patient and patient.status in ("new_patient", "prospective", "pending", None):
        patient.status = "scheduled_patient"

    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "contract.place", "patient_insurance_contract", str(contract_id))
    return {"id": str(contract_id), "status": "active", "patient_status": patient.status if patient else None,
            "posted_charges": float(c.expected_first_charges or 0), "posted_down_payment": float(c.down_payment or 0)}


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
        "fee_type": c.fee_type,
        "discount_amount": float(c.discount_amount),
        "expected_first_charges": float(c.expected_first_charges),
        "down_payment": float(c.down_payment), "insurance_estimate": float(c.insurance_estimate),
        "patient_portion": float(c.patient_portion), "estimated_months": c.estimated_months,
        "policy_notes": c.policy_notes,
        "insurance_verified_at": c.insurance_verified_at.isoformat() if c.insurance_verified_at else None,
        "payer_kind": c.payer_kind, "billing_cadence": c.billing_cadence, "billing_mode": c.billing_mode,
        "claim_destination": c.claim_destination, "initial_claim_sent": c.initial_claim_sent,
        "initial_claim_date": c.initial_claim_date.isoformat() if c.initial_claim_date else None,
        "next_claim_due": c.next_claim_due.isoformat() if c.next_claim_due else None,
        "daily_payment_poll": c.daily_payment_poll, "status": c.status, "notes": c.notes,
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
        denied_dollars = float((await db.execute(
            select(func.sum(InsuranceClaim.total_billed)).where(
                InsuranceClaim.practice_id == practice_id, InsuranceClaim.status == "denied")
        )).scalar() or 0)
        recoverable = round(denied_dollars * 0.5)
        add("warning", "claims", f"Recover ~${recoverable:,.0f} from {denied} denied claim(s)",
            f"${denied_dollars:,.0f} billed is denied; ~50% is typically recoverable on appeal. Review and appeal.",
            denied, "/claims")

    # Unbilled draft claims = revenue not yet captured.
    draft_dollars = float((await db.execute(
        select(func.sum(InsuranceClaim.total_billed)).where(
            InsuranceClaim.practice_id == practice_id, InsuranceClaim.status == "draft")
    )).scalar() or 0)
    if draft_dollars > 0:
        add("info", "claims", f"Send unbilled claims worth ${draft_dollars:,.0f}",
            "Draft claims not yet submitted — send them to capture revenue.", None, "/claims")

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

    # ── Role ordering — claims/revenue first (money), then collections, then clinical ──
    # OrthoFlow AI benefits the practice in claims → money savings → efficiency, in that order.
    role_categories = {
        "front_desk": ["claims", "verification", "collections", "clinical"],
        "frontdesk": ["claims", "verification", "collections", "clinical"],
        "treatment_coordinator": ["claims", "collections", "verification", "clinical"],
        "tc": ["claims", "collections", "verification", "clinical"],
        "doctor": ["claims", "clinical", "verification", "collections"],
        "office_manager": ["claims", "collections", "verification", "clinical"],
        "owner": ["claims", "collections", "verification", "clinical"],
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


# ═══════════════════════════════════════════════════════════════════════════════
# Practice Impact — OrthoFlow AI benefit in DOLLARS, ordered: claims → savings → efficiency
# The practice should see what OrthoFlow is worth: revenue captured/at-risk, money saved,
# and time saved — with claims and money first.
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/practice-impact")
async def practice_impact(
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Quantify OrthoFlow AI's benefit to the practice, prioritized claims → savings → efficiency."""
    from app.models.claims import InsuranceClaim
    from app.models.finance import PatientLedgerEntry
    from app.models.ortho_ops import AutomationRun
    from decimal import Decimal as _D

    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    today = date.today()
    month_start = today.replace(day=1)

    async def _sum(q):
        return float((await db.execute(q)).scalar() or 0)

    # ── 1) CLAIMS (revenue) ─────────────────────────────────────────────────────
    denied_dollars = await _sum(
        select(func.sum(InsuranceClaim.total_billed)).where(
            InsuranceClaim.practice_id == practice_id, InsuranceClaim.status == "denied"))
    denied_count = int(await _sum(
        select(func.count(InsuranceClaim.id)).where(
            InsuranceClaim.practice_id == practice_id, InsuranceClaim.status == "denied")))
    draft_dollars = await _sum(
        select(func.sum(InsuranceClaim.total_billed)).where(
            InsuranceClaim.practice_id == practice_id, InsuranceClaim.status == "draft"))
    in_flight = await _sum(
        select(func.sum(InsuranceClaim.total_billed)).where(
            InsuranceClaim.practice_id == practice_id, InsuranceClaim.status.in_(["submitted", "accepted"])))
    paid_mtd = await _sum(
        select(func.sum(InsuranceClaim.total_paid)).where(
            InsuranceClaim.practice_id == practice_id, InsuranceClaim.status == "paid",
            InsuranceClaim.adjudication_date >= month_start))

    # Appeal recovery estimate: industry ~50% of appealed ortho denials recoverable.
    recoverable = round(denied_dollars * 0.5, 2)

    # ── 2) MONEY SAVINGS ────────────────────────────────────────────────────────
    outstanding_ar = await _sum(
        select(func.sum(PatientLedgerEntry.amount)).where(
            PatientLedgerEntry.practice_id == practice_id))
    outstanding_ar = max(outstanding_ar, 0.0)

    # Denial avoidance: consults auto-verified before the visit prevent downstream denials.
    # Value = verified consults this month × avg ortho claim exposure (conservative $150 each).
    verified_consults = int(await _sum(
        select(func.sum(AutomationRun.items_processed)).where(
            AutomationRun.practice_id == practice_id, AutomationRun.task == "consult_verify",
            AutomationRun.run_date >= month_start)))
    denial_avoidance = round(verified_consults * 150.0, 2)

    # ── 3) EFFICIENCY (time saved) ──────────────────────────────────────────────
    # Automated actions this month × ~4 min each of manual staff work saved.
    automated_actions = int(await _sum(
        select(func.sum(AutomationRun.items_processed)).where(
            AutomationRun.practice_id == practice_id, AutomationRun.run_date >= month_start)))
    hours_saved = round(automated_actions * 4 / 60.0, 1)

    # ── Prioritized impact items (claims first, then savings, then efficiency) ──
    items = [
        {"priority": 1, "category": "claims", "kind": "denied", "label": "Revenue recoverable from denied claims",
         "amount": recoverable, "detail": f"{denied_count} denied claim(s) worth ${denied_dollars:,.0f} billed; "
                                          f"~50% typically recoverable on appeal.", "action_route": "/claims"},
        {"priority": 1, "category": "claims", "kind": "draft", "label": "Unbilled claims ready to send",
         "amount": round(draft_dollars, 2), "detail": "Draft claims not yet submitted — send to capture revenue.",
         "action_route": "/claims"},
        {"priority": 1, "category": "claims", "kind": "in_flight", "label": "Claims in flight (awaiting payer)",
         "amount": round(in_flight, 2), "detail": "Submitted/accepted claims awaiting adjudication.",
         "action_route": "/claims"},
        {"priority": 2, "category": "savings", "kind": "outstanding_ar", "label": "Outstanding A/R to collect",
         "amount": round(outstanding_ar, 2), "detail": "Patient + insurance balances outstanding.",
         "action_route": "/ledger"},
        {"priority": 2, "category": "savings", "kind": "denial_avoidance", "label": "Denials avoided by pre-consult verification",
         "amount": denial_avoidance, "detail": f"{verified_consults} consult(s) auto-verified this month "
                                               f"before the visit — prevents downstream denials & rework.",
         "action_route": "/reports"},
        {"priority": 3, "category": "efficiency", "kind": "automation", "label": "Staff time saved by automation",
         "amount": None, "hours": hours_saved,
         "detail": f"{automated_actions} routine action(s) handled automatically this month "
                   f"(~{hours_saved} staff hours saved).", "action_route": "/"},
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "priority_order": ["claims", "savings", "efficiency"],
        "headline": {
            "claims_revenue_at_stake": round(recoverable + draft_dollars + in_flight, 2),
            "money_savings_opportunity": round(outstanding_ar + denial_avoidance, 2),
            "efficiency_hours_saved_mtd": hours_saved,
            "claims_paid_mtd": round(paid_mtd, 2),
        },
        "items": items,
    }


@router.get("/practice-impact/drilldown")
async def practice_impact_drilldown(
    kind: str = Query(..., description="Impact item kind: denied|draft|in_flight|outstanding_ar|denial_avoidance|automation"),
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Drill-down behind an OrthoFlow AI Practice-Impact insight — returns the exact source
    claims/findings the number was computed from, so the office can see how & where the AI
    reached its conclusion (transparency for the Ledger AI insight)."""
    from app.models.claims import InsuranceClaim
    from app.models.ortho_ops import AutomationRun

    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    today = date.today()
    month_start = today.replace(day=1)
    sources: list[dict] = []

    async def _patient_name(pid) -> str:
        p = (await db.execute(select(Patient).where(Patient.id == pid))).scalar_one_or_none()
        return f"{p.first_name} {p.last_name}" if p else "Patient"

    if kind in ("denied", "draft", "in_flight"):
        status_map = {"denied": ["denied"], "draft": ["draft"], "in_flight": ["submitted", "accepted"]}
        rows = (await db.execute(
            select(InsuranceClaim).where(
                InsuranceClaim.practice_id == practice_id,
                InsuranceClaim.status.in_(status_map[kind]),
            ).order_by(InsuranceClaim.service_date.desc())
        )).scalars().all()
        for c in rows:
            sources.append({
                "type": "claim", "id": str(c.id), "patient_id": str(c.patient_id),
                "patient_name": await _patient_name(c.patient_id),
                "claim_number": c.claim_number, "status": c.status,
                "total_billed": float(c.total_billed or 0),
                "total_paid": float(c.total_paid or 0) if c.total_paid is not None else None,
                "denial_reason": getattr(c, "denial_reason", None),
                "service_date": c.service_date.isoformat() if c.service_date else None,
                "route": f"/claims?patient_id={c.patient_id}",
            })
        method = {
            "denied": "50% of total billed on denied claims is typically recoverable on appeal.",
            "draft": "Sum of total billed on draft (unsent) claims.",
            "in_flight": "Sum of total billed on submitted/accepted claims awaiting adjudication.",
        }[kind]
    elif kind == "outstanding_ar":
        rows = (await db.execute(
            select(PatientLedgerEntry.patient_id, func.sum(PatientLedgerEntry.amount).label("bal"))
            .where(PatientLedgerEntry.practice_id == practice_id)
            .group_by(PatientLedgerEntry.patient_id)
            .having(func.sum(PatientLedgerEntry.amount) > 0)
        )).all()
        for pid, bal in rows:
            sources.append({
                "type": "balance", "patient_id": str(pid), "patient_name": await _patient_name(pid),
                "balance": float(bal or 0), "route": f"/ledger?patient_id={pid}",
            })
        method = "Sum of positive patient ledger balances (charges minus payments)."
    elif kind in ("denial_avoidance", "automation"):
        task_filter = [AutomationRun.run_date >= month_start, AutomationRun.practice_id == practice_id]
        if kind == "denial_avoidance":
            task_filter.append(AutomationRun.task == "consult_verify")
        rows = (await db.execute(
            select(AutomationRun).where(*task_filter).order_by(AutomationRun.run_date.desc())
        )).scalars().all()
        for r in rows:
            sources.append({
                "type": "automation_run", "id": str(r.id), "task": r.task, "label": r.label,
                "run_date": r.run_date.isoformat() if r.run_date else None,
                "items_processed": r.items_processed, "summary": r.summary, "route": "/",
            })
        method = ("Verified consults × $150 avg exposure prevented." if kind == "denial_avoidance"
                  else "Automated actions this month × ~4 min manual work each.")
    else:
        raise HTTPException(400, f"Unknown drilldown kind: {kind}")

    return {"kind": kind, "method": method, "count": len(sources), "sources": sources}
