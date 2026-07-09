"""OrthoFlow API — Claim Submission Workflow (Phase 2 expansion).

Full claim lifecycle: draft → submitted → accepted/rejected → paid/denied → appealed.
Includes line item management, status transitions, and batch operations.
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
from app.models.claims import InsuranceClaim
from app.models.finance import ClaimLineItem, PatientLedgerEntry, InsuranceSubscriber
from app.models.clinical import Patient

router = APIRouter(prefix="/api/v1/claims", tags=["claims-workflow"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LineItemCreate(BaseModel):
    cdt_code: str = Field(..., min_length=5, max_length=10)
    description: str | None = None
    tooth_numbers: str | None = None
    surface: str | None = None
    quantity: int = 1
    billed_amount: Decimal = Field(..., gt=0)
    service_date: date


class ClaimCreateFull(BaseModel):
    patient_id: str
    subscriber_plan_id: str | None = None  # insurance_subscriber to bill
    rendering_provider_npi: str = Field(..., min_length=10, max_length=10)
    billing_provider_npi: str = Field(..., min_length=10, max_length=10)
    prior_auth_number: str | None = None
    line_items: list[LineItemCreate] = Field(..., min_length=1)
    notes: str | None = None


class ClaimStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(accepted|rejected|paid|denied)$")
    denial_codes: list[str] | None = None
    denial_reason: str | None = None
    total_allowed: Decimal | None = None
    total_paid: Decimal | None = None
    patient_responsibility: Decimal | None = None
    adjudication_date: date | None = None
    era_reference: str | None = None


class LineItemAdjudication(BaseModel):
    line_item_id: str
    allowed_amount: Decimal | None = None
    paid_amount: Decimal | None = None
    adjustment_amount: Decimal | None = None
    patient_responsibility: Decimal | None = None
    denial_code: str | None = None
    denial_reason: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
async def list_claims(
    status: str | None = None,
    patient_id: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List claims with optional filters."""
    practice_id = user["practice_id"]
    q = select(InsuranceClaim).where(InsuranceClaim.practice_id == practice_id)
    if status:
        q = q.where(InsuranceClaim.status == status)
    if patient_id:
        q = q.where(InsuranceClaim.patient_id == patient_id)
    q = q.order_by(InsuranceClaim.created_at.desc()).offset((page - 1) * size).limit(size)

    result = await db.execute(q)
    claims = result.scalars().all()

    # Get counts by status
    counts_q = select(
        InsuranceClaim.status, func.count(InsuranceClaim.id)
    ).where(InsuranceClaim.practice_id == practice_id).group_by(InsuranceClaim.status)
    counts_result = await db.execute(counts_q)
    status_counts = {row[0]: row[1] for row in counts_result}

    return {
        "claims": [_claim_dict(c) for c in claims],
        "status_counts": status_counts,
        "page": page,
    }


@router.post("/", status_code=201)
async def create_claim_full(
    body: ClaimCreateFull,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new claim with line items from patient procedures."""
    practice_id = user["practice_id"]

    # Verify patient
    patient = (await db.execute(
        select(Patient).where(Patient.id == body.patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Get insurance info
    payer_id = ""
    payer_type = "commercial"
    subscriber_id_str = ""
    state_code = None

    if body.subscriber_plan_id:
        sub = (await db.execute(
            select(InsuranceSubscriber).where(
                InsuranceSubscriber.id == body.subscriber_plan_id,
                InsuranceSubscriber.practice_id == practice_id,
            )
        )).scalar_one_or_none()
        if sub:
            payer_id = sub.payer_id
            payer_type = sub.plan_type
            subscriber_id_str = sub.subscriber_id
    else:
        # Use primary plan
        sub = (await db.execute(
            select(InsuranceSubscriber).where(
                InsuranceSubscriber.patient_id == body.patient_id,
                InsuranceSubscriber.practice_id == practice_id,
                InsuranceSubscriber.is_active == True,
                InsuranceSubscriber.coverage_type == "primary",
            )
        )).scalar_one_or_none()
        if sub:
            payer_id = sub.payer_id
            payer_type = sub.plan_type
            subscriber_id_str = sub.subscriber_id

    if not payer_id:
        raise HTTPException(422, "No insurance plan found. Add insurance before creating a claim.")

    # Calculate totals
    total_billed = sum(item.billed_amount * item.quantity for item in body.line_items)
    service_date = body.line_items[0].service_date

    # Create claim
    claim = InsuranceClaim(
        practice_id=practice_id,
        patient_id=body.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        subscriber_id=subscriber_id_str,
        payer_id=payer_id,
        payer_type=payer_type,
        state_code=state_code,
        total_billed=total_billed,
        rendering_provider_npi=body.rendering_provider_npi,
        billing_provider_npi=body.billing_provider_npi,
        prior_auth_number=body.prior_auth_number,
        service_date=service_date,
        status="draft",
        cdt_codes=[{"code": li.cdt_code, "fee": float(li.billed_amount)} for li in body.line_items],
    )
    db.add(claim)
    await db.flush()  # get claim.id

    # Create line items
    for i, li in enumerate(body.line_items, 1):
        line = ClaimLineItem(
            claim_id=claim.id,
            line_number=i,
            cdt_code=li.cdt_code,
            description=li.description,
            tooth_numbers=li.tooth_numbers,
            surface=li.surface,
            quantity=li.quantity,
            billed_amount=li.billed_amount,
            service_date=li.service_date,
        )
        db.add(line)

    await db.commit()
    await db.refresh(claim)
    await audit_log(db, practice_id, user["user_id"], "claim.create", "insurance_claim", str(claim.id))

    return {"id": str(claim.id), "status": "draft", "total_billed": float(total_billed), "line_items": len(body.line_items)}


@router.get("/{claim_id}")
async def get_claim_detail(
    claim_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get full claim details including line items."""
    practice_id = user["practice_id"]
    claim = (await db.execute(
        select(InsuranceClaim).where(InsuranceClaim.id == claim_id, InsuranceClaim.practice_id == practice_id)
    )).scalar_one_or_none()
    if not claim:
        raise HTTPException(404, "Claim not found")

    # Get line items
    lines = (await db.execute(
        select(ClaimLineItem).where(ClaimLineItem.claim_id == claim_id).order_by(ClaimLineItem.line_number)
    )).scalars().all()

    result = _claim_dict(claim)
    result["line_items"] = [_line_item_dict(li) for li in lines]
    return result


@router.patch("/{claim_id}/submit")
async def submit_claim(
    claim_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Submit a draft claim to the clearinghouse."""
    practice_id = user["practice_id"]
    claim = (await db.execute(
        select(InsuranceClaim).where(InsuranceClaim.id == claim_id, InsuranceClaim.practice_id == practice_id)
    )).scalar_one_or_none()
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim.status != "draft":
        raise HTTPException(400, f"Cannot submit claim in '{claim.status}' status. Must be 'draft'.")

    # TODO: Call clearinghouse adapter here when live
    # result = await adapter.submit_claim(generate_837d(claim))

    claim.status = "submitted"
    claim.submission_date = datetime.now(timezone.utc)
    await db.commit()

    await audit_log(db, practice_id, user["user_id"], "claim.submit", "insurance_claim", str(claim_id))
    return {"id": str(claim_id), "status": "submitted", "submission_date": claim.submission_date.isoformat()}


@router.patch("/{claim_id}/status")
async def update_claim_status(
    claim_id: UUID,
    body: ClaimStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update claim status after adjudication (from ERA/835 or manual entry)."""
    practice_id = user["practice_id"]
    claim = (await db.execute(
        select(InsuranceClaim).where(InsuranceClaim.id == claim_id, InsuranceClaim.practice_id == practice_id)
    )).scalar_one_or_none()
    if not claim:
        raise HTTPException(404, "Claim not found")

    # Valid transitions
    valid_transitions = {
        "submitted": ["accepted", "rejected"],
        "accepted": ["paid", "denied"],
        "rejected": ["draft"],  # can resubmit
        "denied": ["appealed"],
    }
    current = claim.status
    if current not in valid_transitions or body.status not in valid_transitions.get(current, []):
        raise HTTPException(400, f"Cannot transition from '{current}' to '{body.status}'")

    claim.status = body.status
    if body.denial_codes:
        claim.denial_codes = body.denial_codes
    if body.denial_reason:
        claim.denial_reason = body.denial_reason
    if body.total_allowed is not None:
        claim.total_allowed = body.total_allowed
    if body.total_paid is not None:
        claim.total_paid = body.total_paid
    if body.patient_responsibility is not None:
        claim.patient_responsibility = body.patient_responsibility
    if body.adjudication_date:
        claim.adjudication_date = datetime.combine(body.adjudication_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    if body.era_reference:
        claim.era_reference = body.era_reference

    await db.commit()
    await audit_log(db, practice_id, user["user_id"], f"claim.{body.status}", "insurance_claim", str(claim_id))

    return {"id": str(claim_id), "status": body.status}


@router.patch("/{claim_id}/lines")
async def adjudicate_line_items(
    claim_id: UUID,
    body: list[LineItemAdjudication],
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Apply adjudication data to individual line items (from ERA/835)."""
    practice_id = user["practice_id"]
    claim = (await db.execute(
        select(InsuranceClaim).where(InsuranceClaim.id == claim_id, InsuranceClaim.practice_id == practice_id)
    )).scalar_one_or_none()
    if not claim:
        raise HTTPException(404, "Claim not found")

    for adj in body:
        line = (await db.execute(
            select(ClaimLineItem).where(ClaimLineItem.id == adj.line_item_id, ClaimLineItem.claim_id == claim_id)
        )).scalar_one_or_none()
        if not line:
            continue
        if adj.allowed_amount is not None:
            line.allowed_amount = adj.allowed_amount
        if adj.paid_amount is not None:
            line.paid_amount = adj.paid_amount
        if adj.adjustment_amount is not None:
            line.adjustment_amount = adj.adjustment_amount
        if adj.patient_responsibility is not None:
            line.patient_responsibility = adj.patient_responsibility
        if adj.denial_code:
            line.denial_code = adj.denial_code
        if adj.denial_reason:
            line.denial_reason = adj.denial_reason

    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "claim.adjudicate_lines", "insurance_claim", str(claim_id))
    return {"status": "updated", "lines_processed": len(body)}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _claim_dict(c: InsuranceClaim) -> dict:
    return {
        "id": str(c.id),
        "patient_id": c.patient_id,
        "patient_name": c.patient_name,
        "subscriber_id": c.subscriber_id,
        "payer_id": c.payer_id,
        "payer_type": c.payer_type,
        "claim_number": c.claim_number,
        "status": c.status,
        "total_billed": float(c.total_billed) if c.total_billed else None,
        "total_allowed": float(c.total_allowed) if c.total_allowed else None,
        "total_paid": float(c.total_paid) if c.total_paid else None,
        "patient_responsibility": float(c.patient_responsibility) if c.patient_responsibility else None,
        "service_date": c.service_date.isoformat() if c.service_date else None,
        "submission_date": c.submission_date.isoformat() if c.submission_date else None,
        "adjudication_date": c.adjudication_date.isoformat() if c.adjudication_date else None,
        "denial_codes": c.denial_codes,
        "denial_reason": c.denial_reason,
        "prior_auth_number": c.prior_auth_number,
        "era_reference": c.era_reference,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _line_item_dict(li: ClaimLineItem) -> dict:
    return {
        "id": str(li.id),
        "line_number": li.line_number,
        "cdt_code": li.cdt_code,
        "description": li.description,
        "tooth_numbers": li.tooth_numbers,
        "surface": li.surface,
        "quantity": li.quantity,
        "billed_amount": float(li.billed_amount),
        "allowed_amount": float(li.allowed_amount) if li.allowed_amount else None,
        "paid_amount": float(li.paid_amount) if li.paid_amount else None,
        "adjustment_amount": float(li.adjustment_amount) if li.adjustment_amount else None,
        "patient_responsibility": float(li.patient_responsibility) if li.patient_responsibility else None,
        "denial_code": li.denial_code,
        "denial_reason": li.denial_reason,
        "service_date": li.service_date.isoformat() if li.service_date else None,
    }
