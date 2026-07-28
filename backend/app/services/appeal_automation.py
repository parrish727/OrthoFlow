"""Same-Day Appeal Automation — orchestrates denial review, appeal generation, and resubmission."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claims import InsuranceClaim
from app.models.finance import ClaimLineItem
from app.services.stedi import StediClient, StediError
from app.core.audit import audit_log

logger = logging.getLogger(__name__)


async def _get_claim_with_lines(db: AsyncSession, claim_id: str, practice_id: str) -> tuple:
    """Load claim and its line items from DB."""
    claim = (await db.execute(
        select(InsuranceClaim).where(
            InsuranceClaim.id == claim_id,
            InsuranceClaim.practice_id == practice_id,
        )
    )).scalar_one_or_none()

    if not claim:
        return None, []

    lines = (await db.execute(
        select(ClaimLineItem).where(ClaimLineItem.claim_id == claim_id).order_by(ClaimLineItem.line_number)
    )).scalars().all()

    return claim, lines


async def _build_denial_context(claim: InsuranceClaim, lines: list) -> dict:
    """Build context dict for AI denial review."""
    return {
        "patient_name": claim.patient_name,
        "payer_id": claim.payer_id,
        "payer_type": claim.payer_type,
        "service_date": claim.service_date.isoformat() if claim.service_date else "unknown",
        "submission_date": claim.submission_date.isoformat() if claim.submission_date else "unknown",
        "total_billed": float(claim.total_billed) if claim.total_billed else 0,
        "prior_auth": claim.prior_auth_number,
        "denial_codes": claim.denial_codes or [],
        "denial_reason": claim.denial_reason or "Not specified",
        "cdt_codes": [li.cdt_code for li in lines],
        "line_items": [
            {
                "code": li.cdt_code,
                "billed": float(li.billed_amount),
                "denied": li.denial_code is not None,
                "denial_code": li.denial_code,
                "denial_reason": li.denial_reason,
            }
            for li in lines
        ],
    }


async def _call_ai_denial_review(context: dict) -> dict:
    """Call Anthropic Claude for denial analysis — reuses logic pattern from ai_claims.py."""
    import os
    import httpx
    from app.core.config import settings

    prompt = f"""You are an orthodontic insurance claims specialist. Analyze this denied claim and determine if an appeal should be filed.

CLAIM DETAILS:
- Patient: {context['patient_name']}
- Payer: {context['payer_id']} ({context['payer_type']})
- Service Date: {context['service_date']}
- Total Billed: ${context['total_billed']:.2f}
- Prior Authorization: {context['prior_auth'] or 'None'}
- CDT Codes: {', '.join(context['cdt_codes'])}

DENIAL INFORMATION:
- Denial Codes: {', '.join(str(c) for c in context['denial_codes']) if context['denial_codes'] else 'None'}
- Denial Reason: {context['denial_reason']}

LINE ITEMS:
{chr(10).join(f"  - {li['code']}: ${li['billed']:.2f}" + (f" [DENIED: {li['denial_code']} - {li['denial_reason']}]" if li['denied'] else " [OK]") for li in context['line_items'])}

RESPOND IN THIS EXACT FORMAT (no markdown):
APPEAL_RECOMMENDED: [yes or no]
SUCCESS_LIKELIHOOD: [high, medium, or low]
APPEAL_LETTER: [If appeal recommended, write a professional appeal letter addressed to the payer's claims department. Include clinical justification. If not recommended, write "N/A"]
CORRECTIVE_ACTIONS: [Comma-separated list of corrections needed]"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
    except Exception as e:
        logger.error(f"AI denial review failed: {e}")
        return {
            "appeal_recommended": False,
            "success_likelihood": "low",
            "appeal_letter": None,
            "corrective_actions": [],
            "error": str(e),
        }

    # Parse response
    appeal_recommended = False
    success_likelihood = "low"
    appeal_letter = None
    corrective_actions: list[str] = []

    current_field = None
    current_value: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("APPEAL_RECOMMENDED:"):
            if current_field == "appeal_letter" and current_value:
                appeal_letter = "\n".join(current_value).strip()
            current_field = "appeal_recommended"
            val = stripped[len("APPEAL_RECOMMENDED:"):].strip().lower()
            appeal_recommended = val in ("yes", "true")
        elif stripped.startswith("SUCCESS_LIKELIHOOD:"):
            current_field = "success_likelihood"
            success_likelihood = stripped[len("SUCCESS_LIKELIHOOD:"):].strip().lower()
        elif stripped.startswith("APPEAL_LETTER:"):
            current_field = "appeal_letter"
            first_line = stripped[len("APPEAL_LETTER:"):].strip()
            current_value = [first_line] if first_line else []
        elif stripped.startswith("CORRECTIVE_ACTIONS:"):
            if current_field == "appeal_letter" and current_value:
                appeal_letter = "\n".join(current_value).strip()
            current_field = "corrective_actions"
            val = stripped[len("CORRECTIVE_ACTIONS:"):].strip()
            corrective_actions = [a.strip() for a in val.split(",") if a.strip()]
        else:
            if current_field == "appeal_letter":
                current_value.append(stripped)

    # Final capture for appeal letter if it was the last field
    if current_field == "appeal_letter" and current_value and not appeal_letter:
        appeal_letter = "\n".join(current_value).strip()

    if appeal_letter and appeal_letter.lower() == "n/a":
        appeal_letter = None

    return {
        "appeal_recommended": appeal_recommended,
        "success_likelihood": success_likelihood,
        "appeal_letter": appeal_letter,
        "corrective_actions": corrective_actions,
    }


def _build_resubmission_data(claim: InsuranceClaim, lines: list) -> dict:
    """Build claim_data dict from the existing claim for resubmission."""
    return {
        "patient_control_number": str(claim.id),
        "total_billed": str(claim.total_billed),
        "subscriber_id": claim.subscriber_id,
        "subscriber_first_name": "",  # Would need patient lookup in production
        "subscriber_last_name": claim.patient_name,
        "patient_first_name": "",
        "patient_last_name": claim.patient_name,
        "billing_provider_npi": claim.billing_provider_npi,
        "rendering_provider_npi": claim.rendering_provider_npi,
        "payer_id": claim.payer_id,
        "prior_auth_number": claim.prior_auth_number,
        "service_lines": [
            {
                "service_date": claim.service_date.isoformat() if claim.service_date else "",
                "cdt_code": li.cdt_code,
                "billed_amount": str(li.billed_amount),
                "tooth_number": getattr(li, "tooth_number", None),
                "tooth_surface": getattr(li, "tooth_surface", None),
            }
            for li in lines
        ],
        "diagnosis_codes": claim.cdt_codes if isinstance(claim.cdt_codes, list) else [],
    }


async def process_denial(claim_id: str, practice_id: str, db: AsyncSession) -> dict:
    """Orchestrate same-day appeal: review denial → generate appeal → resubmit.

    Steps:
    1. Load claim from DB
    2. Call AI denial review
    3. If appeal recommended: generate appeal letter
    4. Format as resubmission with narrative attachment
    5. Submit via StediClient.resubmit_claim()
    6. Update claim status to 'appealed'
    7. Create audit log entry
    8. Return result summary
    """
    # Step 1: Load claim
    claim, lines = await _get_claim_with_lines(db, claim_id, practice_id)
    if not claim:
        return {
            "success": False,
            "claim_id": claim_id,
            "action": "none",
            "reason": "Claim not found",
        }

    # Don't re-appeal claims already appealed or paid
    if claim.status in ("appealed", "paid", "accepted"):
        return {
            "success": False,
            "claim_id": claim_id,
            "action": "skipped",
            "reason": f"Claim already in status: {claim.status}",
        }

    # Step 2: AI denial review
    context = await _build_denial_context(claim, lines)
    review = await _call_ai_denial_review(context)

    if review.get("error"):
        await audit_log(
            db, practice_id, None, "appeal.ai_review_failed",
            "insurance_claim", claim_id,
            details=f"AI review error: {review['error'][:200]}",
        )
        await db.commit()
        return {
            "success": False,
            "claim_id": claim_id,
            "action": "review_failed",
            "reason": review["error"],
        }

    # Step 3: Check if appeal is recommended
    if not review["appeal_recommended"]:
        await audit_log(
            db, practice_id, None, "appeal.not_recommended",
            "insurance_claim", claim_id,
            details=f"Likelihood: {review['success_likelihood']}",
        )
        await db.commit()
        return {
            "success": True,
            "claim_id": claim_id,
            "action": "no_appeal",
            "reason": "AI determined appeal not recommended",
            "success_likelihood": review["success_likelihood"],
            "corrective_actions": review["corrective_actions"],
        }

    # Step 4 + 5: Format and resubmit via Stedi
    appeal_letter = review["appeal_letter"] or "Appeal: clinical necessity for services rendered."
    resubmission_data = _build_resubmission_data(claim, lines)

    try:
        stedi = StediClient()
        result = await stedi.resubmit_claim(
            original_claim_id=str(claim.id),
            corrected_data=resubmission_data,
            appeal_narrative=appeal_letter,
        )
    except StediError as e:
        logger.error(f"Stedi resubmission failed for claim {claim_id}: {e.message}")
        await audit_log(
            db, practice_id, None, "appeal.submission_failed",
            "insurance_claim", claim_id,
            details=f"Stedi error: {e.message[:200]}",
        )
        await db.commit()
        return {
            "success": False,
            "claim_id": claim_id,
            "action": "submission_failed",
            "reason": e.message,
        }

    # Step 6: Update claim status
    if result.success:
        claim.status = "appealed"
        claim.appeal_text = appeal_letter
        claim.appeal_date = datetime.now(timezone.utc)
        claim.appeal_status = "submitted"

        # Step 7: Audit log
        await audit_log(
            db, practice_id, None, "appeal.submitted",
            "insurance_claim", claim_id,
            details=f"Resubmitted via Stedi. New claim ID: {result.claim_id}, tracking: {result.tracking_number}",
        )
        await db.commit()

        return {
            "success": True,
            "claim_id": claim_id,
            "action": "appealed",
            "new_claim_id": result.claim_id,
            "tracking_number": result.tracking_number,
            "appeal_letter_length": len(appeal_letter),
            "success_likelihood": review["success_likelihood"],
        }
    else:
        await audit_log(
            db, practice_id, None, "appeal.submission_rejected",
            "insurance_claim", claim_id,
            details=f"Stedi rejected resubmission: {result.errors}",
        )
        await db.commit()

        return {
            "success": False,
            "claim_id": claim_id,
            "action": "rejected",
            "reason": "Stedi rejected the resubmission",
            "errors": result.errors,
        }
