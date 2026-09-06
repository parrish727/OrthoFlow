"""OrthoFlow API — Insurance Eligibility Verification.

Real-time eligibility check (270/271 transaction) via Stedi.

PRECOGNITIVE INTENT (see .kiro/steering/product-context.md):
The Treatment Coordinator shouldn't have to hunt for problems. This endpoint verifies
coverage AND proactively surfaces what the TC needs to act on next — benefit exhaustion,
deductible remaining, plans nearing termination, ortho lifetime max nearly used — as
plain-language `alerts` returned alongside the raw result.

Sandbox behavior: when the patient's payer maps to a Stedi dental test payer and Stedi is
enabled, we send a LIVE mock 270/271 to Stedi and persist the returned benefits snapshot.
Otherwise we gracefully fall back to computing eligibility from stored benefit data so the
workflow never breaks in a demo.
"""
import logging
from uuid import UUID
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.core.config import settings
from app.models.finance import InsuranceSubscriber
from app.models.clinical import Patient
from app.services.stedi_payers import resolve_stedi_test_payer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/eligibility", tags=["eligibility"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class EligibilityCheckRequest(BaseModel):
    patient_id: str
    subscriber_plan_id: str | None = None  # if None, checks primary plan


class BenefitAlert(BaseModel):
    """A precognitive, plain-language signal for the Treatment Coordinator."""
    severity: str  # info | warning | critical
    code: str      # machine key, e.g. "ORTHO_MAX_NEAR_LIMIT"
    message: str   # human-readable guidance


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
    source: str            # "stedi_live" | "stored_benefits"
    application_mode: str | None = None   # "test" | "production" (Stedi)
    trace_id: str | None = None
    alerts: list[BenefitAlert] = []
    errors: list[str] = []


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/check", response_model=EligibilityResult)
async def check_eligibility(
    body: EligibilityCheckRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Verify a patient's insurance eligibility in real-time and surface next actions.

    Tries a live Stedi (test-mode) 270/271 when the payer is mapped; otherwise computes
    from stored benefits. Always returns `alerts` — the things the TC should act on.
    """
    practice_id = user["practice_id"]

    patient = (await db.execute(
        select(Patient).where(Patient.id == body.patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    sub = await _resolve_plan(db, body, practice_id)
    if not sub:
        raise HTTPException(404, "No active insurance plan found for this patient")

    now = datetime.now(timezone.utc)

    # ── Attempt a live Stedi eligibility check (test mode) ─────────────────────
    stedi_result = None
    source = "stored_benefits"
    application_mode = None
    trace_id = None
    stedi_errors: list[str] = []

    mapping = resolve_stedi_test_payer(sub.payer_id)
    if settings.STEDI_ENABLED and settings.STEDI_API_KEY and mapping:
        try:
            from app.services.stedi import StediClient  # lazy import; avoids httpx at module load
            client = StediClient()
            # In sandbox we must send Stedi's exact mock subscriber creds to get a mock 271.
            # In production this block uses the patient's real subscriber data instead.
            if settings.ENVIRONMENT == "production" and settings.STEDI_LIVE_CLAIMS:
                subscriber_payload = {
                    "trading_partner_service_id": mapping["stedi_payer_id"],
                    "first_name": sub.subscriber_first_name or patient.first_name,
                    "last_name": sub.subscriber_last_name or patient.last_name,
                    "member_id": sub.subscriber_id,
                    "date_of_birth": _fmt_dob(sub.subscriber_dob or patient.date_of_birth),
                }
            else:
                mock = mapping["mock_subscriber"] or {}
                subscriber_payload = {
                    "trading_partner_service_id": mapping["stedi_payer_id"],
                    "first_name": mock.get("first_name", ""),
                    "last_name": mock.get("last_name", ""),
                    "member_id": mock.get("member_id", ""),
                    "date_of_birth": mock.get("date_of_birth", ""),
                }
            stedi_result = await client.check_eligibility(subscriber_payload)
            if stedi_result.errors:
                stedi_errors = stedi_result.errors
                application_mode = stedi_result.application_mode
                trace_id = stedi_result.trace_id
            else:
                source = "stedi_live"
                application_mode = stedi_result.application_mode
                trace_id = stedi_result.trace_id
        except Exception as e:  # never let a clearinghouse hiccup break the TC's workflow
            logger.warning(f"Stedi eligibility failed, falling back to stored benefits: {e}")
            stedi_errors = [f"Clearinghouse unavailable — showing stored benefits ({e})"]

    # ── Compute coverage + benefits (from Stedi when live, else stored) ────────
    errors: list[str] = []
    coverage_active = sub.is_active
    if sub.termination_date and sub.termination_date < now.date():
        coverage_active = False
        errors.append("Plan terminated")
    if sub.effective_date and sub.effective_date > now.date():
        coverage_active = False
        errors.append("Plan not yet effective")

    if source == "stedi_live" and stedi_result is not None:
        coverage_active = stedi_result.coverage_active
        plan_name = stedi_result.plan_name or sub.plan_name
        copay = stedi_result.copay if stedi_result.copay is not None else _to_float(sub.copay_amount)
        deductible_remaining = (
            stedi_result.deductible_remaining
            if stedi_result.deductible_remaining is not None
            else _deductible_remaining(sub)
        )
        remaining_benefit = (
            stedi_result.remaining_benefit
            if stedi_result.remaining_benefit is not None
            else _annual_remaining(sub)
        )
    else:
        plan_name = sub.plan_name
        copay = _to_float(sub.copay_amount)
        deductible_remaining = _deductible_remaining(sub)
        remaining_benefit = _annual_remaining(sub)

    ortho_remaining = _ortho_remaining(sub)
    eligible = coverage_active and not errors

    # Persist eligibility snapshot to the subscriber record.
    sub.last_eligibility_check = now
    sub.eligibility_status = "active" if eligible else "inactive"
    await db.commit()

    await audit_log(db, practice_id, user["user_id"], "eligibility.check", "insurance_subscriber", str(sub.id))

    # ── Precognitive alerts — what the TC should act on next ───────────────────
    alerts = _build_alerts(sub, coverage_active, remaining_benefit, ortho_remaining, deductible_remaining, now.date())

    return EligibilityResult(
        eligible=eligible,
        subscriber_id=sub.subscriber_id,
        payer_name=sub.payer_name,
        plan_name=plan_name,
        coverage_active=coverage_active,
        effective_date=sub.effective_date.isoformat() if sub.effective_date else None,
        termination_date=sub.termination_date.isoformat() if sub.termination_date else None,
        remaining_benefit=remaining_benefit,
        ortho_remaining=ortho_remaining,
        copay=copay,
        deductible_remaining=deductible_remaining,
        last_checked=now.isoformat(),
        source=source,
        application_mode=application_mode,
        trace_id=trace_id,
        alerts=alerts,
        errors=errors + stedi_errors,
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
                "stedi_mapped": resolve_stedi_test_payer(p.payer_id) is not None,
            }
            for p in plans
        ],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _resolve_plan(db: AsyncSession, body: EligibilityCheckRequest, practice_id) -> InsuranceSubscriber | None:
    if body.subscriber_plan_id:
        return (await db.execute(
            select(InsuranceSubscriber).where(
                InsuranceSubscriber.id == body.subscriber_plan_id,
                InsuranceSubscriber.practice_id == practice_id,
            )
        )).scalar_one_or_none()
    return (await db.execute(
        select(InsuranceSubscriber).where(
            InsuranceSubscriber.patient_id == body.patient_id,
            InsuranceSubscriber.practice_id == practice_id,
            InsuranceSubscriber.is_active == True,
            InsuranceSubscriber.coverage_type == "primary",
        )
    )).scalar_one_or_none()


def _to_float(v) -> float | None:
    return float(v) if v is not None else None


def _annual_remaining(sub: InsuranceSubscriber) -> float | None:
    if sub.annual_max is not None and sub.annual_used is not None:
        return float(sub.annual_max - sub.annual_used)
    return None


def _ortho_remaining(sub: InsuranceSubscriber) -> float | None:
    if sub.ortho_lifetime_max is not None and sub.ortho_lifetime_used is not None:
        return float(sub.ortho_lifetime_max - sub.ortho_lifetime_used)
    return None


def _deductible_remaining(sub: InsuranceSubscriber) -> float | None:
    if sub.deductible_amount is not None and sub.deductible_met is not None:
        return float(sub.deductible_amount - sub.deductible_met)
    return None


def _fmt_dob(d) -> str:
    """Format a date as Stedi's YYYYMMDD."""
    if isinstance(d, (date, datetime)):
        return d.strftime("%Y%m%d")
    return ""


def _build_alerts(
    sub: InsuranceSubscriber,
    coverage_active: bool,
    remaining_benefit: float | None,
    ortho_remaining: float | None,
    deductible_remaining: float | None,
    today: date,
) -> list[BenefitAlert]:
    """Anticipate what the Treatment Coordinator needs to know before they ask."""
    alerts: list[BenefitAlert] = []

    if not coverage_active:
        alerts.append(BenefitAlert(
            severity="critical", code="COVERAGE_INACTIVE",
            message="Coverage is not active. Verify the plan before scheduling billable treatment.",
        ))

    # Plan terminating within 60 days — start next-year planning / re-verification now.
    if sub.termination_date:
        days = (sub.termination_date - today).days
        if 0 <= days <= 60:
            alerts.append(BenefitAlert(
                severity="warning", code="PLAN_TERMINATING_SOON",
                message=f"Plan terminates in {days} days ({sub.termination_date.isoformat()}). "
                        f"Confirm continuation of benefits and re-verify before then.",
            ))

    # Ortho lifetime max nearly exhausted — flag before booking more billable ortho visits.
    if ortho_remaining is not None and sub.ortho_lifetime_max:
        pct_left = ortho_remaining / float(sub.ortho_lifetime_max) if sub.ortho_lifetime_max else 1
        if ortho_remaining <= 0:
            alerts.append(BenefitAlert(
                severity="critical", code="ORTHO_MAX_EXHAUSTED",
                message="Orthodontic lifetime maximum is exhausted. Remaining treatment will be patient responsibility.",
            ))
        elif pct_left <= 0.15:
            alerts.append(BenefitAlert(
                severity="warning", code="ORTHO_MAX_NEAR_LIMIT",
                message=f"Only ${ortho_remaining:,.2f} of ortho lifetime benefit remains "
                        f"(~{pct_left*100:.0f}%). Discuss patient responsibility for remaining phases.",
            ))

    # Annual max nearly used — coordinate timing of elective procedures across benefit years.
    if remaining_benefit is not None and sub.annual_max:
        pct_left = remaining_benefit / float(sub.annual_max) if sub.annual_max else 1
        if remaining_benefit <= 0:
            alerts.append(BenefitAlert(
                severity="warning", code="ANNUAL_MAX_EXHAUSTED",
                message="Annual maximum reached. Consider deferring elective procedures to the next benefit year.",
            ))
        elif pct_left <= 0.20:
            alerts.append(BenefitAlert(
                severity="info", code="ANNUAL_MAX_LOW",
                message=f"${remaining_benefit:,.2f} of annual maximum remains (~{pct_left*100:.0f}%).",
            ))

    # Deductible not yet met — set patient expectations on out-of-pocket at the visit.
    if deductible_remaining is not None and deductible_remaining > 0:
        alerts.append(BenefitAlert(
            severity="info", code="DEDUCTIBLE_OUTSTANDING",
            message=f"${deductible_remaining:,.2f} deductible remaining — collect or set expectations at check-in.",
        ))

    # Stale verification — nudge a re-check if it's been a while.
    if sub.last_eligibility_check:
        stale_days = (today - sub.last_eligibility_check.date()).days
        if stale_days >= 30:
            alerts.append(BenefitAlert(
                severity="info", code="VERIFICATION_STALE",
                message=f"Last verified {stale_days} days ago. Re-verify to ensure current benefits.",
            ))

    return alerts
