"""OrthoFlow API — Insurance Eligibility Verification.

Real-time eligibility check (270/271 transaction) via clearinghouse adapter.
Currently uses mock responses — real integration plugs in via the ClearinghouseAdapter protocol.
"""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.finance import InsuranceSubscriber
from app.models.clinical import Patient

router = APIRouter(prefix="/api/v1/eligibility", tags=["eligibility"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class EligibilityCheckRequest(BaseModel):
    patient_id: str
    subscriber_plan_id: str | None = None  # if None, checks primary plan


class EligibilityResult(BaseModel):
    eligible: bool
    subscriber_id: str
    payer_name: str
    plan_name: str | None
    coverage_active: bool
    effective_date: str | None
    termination_date: str | None
    remaining_benefit: float | None
    ortho_remaining: float | None
    copay: float | None
    deductible_remaining: float | None
    last_checked: str
    errors: list[str]


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/check", response_model=EligibilityResult)
async def check_eligibility(
    body: EligibilityCheckRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Verify a patient's insurance eligibility in real-time.

    Checks coverage status, remaining benefits, deductible, and ortho-specific limits.
    Updates the insurance_subscriber record with the latest eligibility status.
    """
    practice_id = user["practice_id"]

    # Verify patient
    patient = (await db.execute(
        select(Patient).where(Patient.id == body.patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Get the insurance plan to check
    if body.subscriber_plan_id:
        sub = (await db.execute(
            select(InsuranceSubscriber).where(
                InsuranceSubscriber.id == body.subscriber_plan_id,
                InsuranceSubscriber.practice_id == practice_id,
            )
        )).scalar_one_or_none()
    else:
        # Default to primary active plan
        sub = (await db.execute(
            select(InsuranceSubscriber).where(
                InsuranceSubscriber.patient_id == body.patient_id,
                InsuranceSubscriber.practice_id == practice_id,
                InsuranceSubscriber.is_active == True,
                InsuranceSubscriber.coverage_type == "primary",
            )
        )).scalar_one_or_none()

    if not sub:
        raise HTTPException(404, "No active insurance plan found for this patient")

    # ── Call clearinghouse for real-time eligibility (270/271) ─────────────────
    # For now, we return computed eligibility based on stored benefit data.
    # When clearinghouse integration is live, this calls:
    #   adapter.verify_eligibility(sub.subscriber_id, sub.payer_id, practice_npi)
    # and updates the subscriber record with fresh data from the payer.

    now = datetime.now(timezone.utc)
    errors: list[str] = []

    # Determine eligibility
    coverage_active = sub.is_active
    if sub.termination_date and sub.termination_date < now.date():
        coverage_active = False
        errors.append("Plan terminated")
    if sub.effective_date and sub.effective_date > now.date():
        coverage_active = False
        errors.append("Plan not yet effective")

    eligible = coverage_active and len(errors) == 0

    # Calculate remaining benefits
    remaining_benefit = None
    if sub.annual_max is not None and sub.annual_used is not None:
        remaining_benefit = float(sub.annual_max - sub.annual_used)

    ortho_remaining = None
    if sub.ortho_lifetime_max is not None and sub.ortho_lifetime_used is not None:
        ortho_remaining = float(sub.ortho_lifetime_max - sub.ortho_lifetime_used)

    deductible_remaining = None
    if sub.deductible_amount is not None and sub.deductible_met is not None:
        deductible_remaining = float(sub.deductible_amount - sub.deductible_met)

    # Update subscriber with check timestamp
    sub.last_eligibility_check = now
    sub.eligibility_status = "active" if eligible else "inactive"
    await db.commit()

    await audit_log(db, practice_id, user["user_id"], "eligibility.check", "insurance_subscriber", str(sub.id))

    return EligibilityResult(
        eligible=eligible,
        subscriber_id=sub.subscriber_id,
        payer_name=sub.payer_name,
        plan_name=sub.plan_name,
        coverage_active=coverage_active,
        effective_date=sub.effective_date.isoformat() if sub.effective_date else None,
        termination_date=sub.termination_date.isoformat() if sub.termination_date else None,
        remaining_benefit=remaining_benefit,
        ortho_remaining=ortho_remaining,
        copay=float(sub.copay_amount) if sub.copay_amount else None,
        deductible_remaining=deductible_remaining,
        last_checked=now.isoformat(),
        errors=errors,
    )


@router.get("/status/{patient_id}")
async def get_eligibility_status(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get the last known eligibility status for all of a patient's plans."""
    practice_id = user["practice_id"]
    result = await db.execute(
        select(InsuranceSubscriber).where(
            InsuranceSubscriber.patient_id == patient_id,
            InsuranceSubscriber.practice_id == practice_id,
            InsuranceSubscriber.is_active == True,
        )
    )
    plans = result.scalars().all()

    return {
        "patient_id": str(patient_id),
        "plans": [
            {
                "id": str(p.id),
                "payer_name": p.payer_name,
                "coverage_type": p.coverage_type,
                "eligibility_status": p.eligibility_status or "unknown",
                "last_checked": p.last_eligibility_check.isoformat() if p.last_eligibility_check else None,
            }
            for p in plans
        ],
    }
