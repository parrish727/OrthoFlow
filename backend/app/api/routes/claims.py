"""OrthoFlow API — Payer Configuration & Claims Endpoints (v2.1)."""
from uuid import UUID
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.claims import InsuranceClaim, PriorAuthorization, PracticePayerConfig
from app.services.cdt_codes import validate_claim_codes, get_code_info, ORTHO_CDT_CODES
from app.services.medicaid_rules import validate_claim_against_state, get_supported_states, get_state_rules

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class PayerConfigCreate(BaseModel):
    payer_id: str
    payer_name: str
    payer_type: str
    state_code: str | None = None
    npi: str
    tax_id: str
    clearinghouse: str
    clearinghouse_id: str
    fee_schedule: dict | None = None
    submission_method: str = "electronic"

class ClaimCreate(BaseModel):
    patient_id: str
    patient_name: str
    subscriber_id: str
    payer_id: str
    payer_type: str
    state_code: str | None = None
    cdt_codes: list[dict]
    rendering_provider_npi: str
    billing_provider_npi: str
    service_date: date
    prior_auth_number: str | None = None


# ── Payer Config Endpoints ────────────────────────────────────────────────────

@router.get("/payers")
async def list_payers(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    practice_id = user["practice_id"]
    result = await db.execute(select(PracticePayerConfig).where(PracticePayerConfig.practice_id == practice_id))
    return {"payers": [row.__dict__ for row in result.scalars().all()]}


@router.post("/payers")
async def create_payer(body: PayerConfigCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    practice_id = user["practice_id"]
    config = PracticePayerConfig(practice_id=practice_id, **body.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return {"id": str(config.id), "status": "created"}


@router.delete("/payers/{payer_config_id}")
async def delete_payer(payer_config_id: UUID, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(PracticePayerConfig).where(PracticePayerConfig.id == payer_config_id, PracticePayerConfig.practice_id == user["practice_id"]))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "Payer config not found")
    await db.delete(config)
    await db.commit()
    return {"status": "deleted"}


# ── Claims Endpoints ──────────────────────────────────────────────────────────

@router.get("/claims")
async def list_claims(status: str | None = None, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    practice_id = user["practice_id"]
    q = select(InsuranceClaim).where(InsuranceClaim.practice_id == practice_id)
    if status:
        q = q.where(InsuranceClaim.status == status)
    result = await db.execute(q.order_by(InsuranceClaim.created_at.desc()))
    return {"claims": [row.__dict__ for row in result.scalars().all()]}


@router.post("/claims")
async def create_claim(body: ClaimCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    practice_id = user["practice_id"]
    # Validate CDT codes
    code_results = validate_claim_codes(body.cdt_codes)
    errors = [r.errors for r in code_results if not r.valid]
    if errors:
        raise HTTPException(422, {"detail": "Invalid CDT codes", "errors": errors})

    # Calculate total billed
    total_billed = sum(Decimal(str(c.get("fee", 0))) * c.get("units", 1) for c in body.cdt_codes)

    # Validate against state Medicaid rules if applicable
    warnings = []
    if body.payer_type == "medicaid" and body.state_code:
        for code_item in body.cdt_codes:
            result = validate_claim_against_state(body.state_code, code_item["code"], billed_amount=Decimal(str(code_item.get("fee", 0))))
            if not result.allowed:
                raise HTTPException(422, {"detail": f"Medicaid rule violation for {code_item['code']}", "errors": result.errors})
            warnings.extend(result.warnings)

    claim = InsuranceClaim(practice_id=practice_id, total_billed=total_billed, **body.model_dump())
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return {"id": str(claim.id), "status": "draft", "total_billed": float(total_billed), "warnings": warnings}


@router.patch("/claims/{claim_id}/submit")
async def submit_claim(claim_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InsuranceClaim).where(InsuranceClaim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim.status != "draft":
        raise HTTPException(400, f"Cannot submit claim in '{claim.status}' status")
    claim.status = "submitted"
    from datetime import datetime, timezone
    claim.submission_date = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(claim.id), "status": "submitted"}


# ── Reference Data ────────────────────────────────────────────────────────────

@router.get("/cdt-codes")
async def list_cdt_codes():
    return {"codes": [{"code": k, **v} for k, v in ORTHO_CDT_CODES.items()]}


@router.get("/medicaid/states")
async def list_medicaid_states():
    states = get_supported_states()
    return {"states": [{"code": s, "rules": get_state_rules(s)} for s in states]}
