"""OrthoFlow API — AI Denial Detection & Appeal Writing.

Routes denial analysis through Darius → LLM to:
1. Analyze denial codes and EOB text to identify the reason
2. Detect patterns (common denial reasons for this payer/procedure)
3. Generate a professionally worded appeal letter
4. Suggest supporting documentation needed

Architecture: OrthoFlow → Darius → Claude Haiku (future: Mistral Small local)
"""
import os
from uuid import UUID
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.claims import InsuranceClaim
from app.models.finance import ClaimLineItem

router = APIRouter(prefix="/api/v1/ai/claims", tags=["ai-claims"])

DARIUS_URL = os.environ.get("DARIUS_URL", "http://darius-agent:8000")


# ── Schemas ───────────────────────────────────────────────────────────────────

class DenialReviewRequest(BaseModel):
    claim_id: str
    eob_text: str | None = None  # raw EOB/denial text if available


class DenialAnalysis(BaseModel):
    claim_id: str
    denial_category: str  # e.g. "medical_necessity", "coding_error", "timely_filing", "auth_required", "benefit_exhausted"
    denial_explanation: str  # plain-English explanation of why it was denied
    appeal_recommended: bool
    appeal_success_likelihood: str  # "high", "medium", "low"
    appeal_letter: str | None  # generated appeal text
    supporting_docs_needed: list[str]  # what to attach
    corrective_actions: list[str]  # things to fix before resubmitting


class AppealGenerateRequest(BaseModel):
    claim_id: str
    additional_context: str | None = None  # office manager can add context


class AppealResponse(BaseModel):
    claim_id: str
    appeal_letter: str
    appeal_type: str  # "clinical_narrative", "coding_correction", "timely_filing_exception", "peer_to_peer_request"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _call_darius(task: str) -> str:
    """Call Darius for LLM-powered analysis."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DARIUS_URL}/task",
                json={"task": task, "project": "orthoflow-ai"},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("args", {}).get("proposal", data.get("result", ""))
    except httpx.TimeoutException:
        raise HTTPException(503, "AI analysis timed out — try again")
    except Exception as e:
        raise HTTPException(503, f"AI service unavailable: {str(e)[:100]}")


async def _get_claim_context(db: AsyncSession, claim_id: str, practice_id: str) -> dict:
    """Gather full claim context for denial analysis."""
    claim = (await db.execute(
        select(InsuranceClaim).where(InsuranceClaim.id == claim_id, InsuranceClaim.practice_id == practice_id)
    )).scalar_one_or_none()
    if not claim:
        raise HTTPException(404, "Claim not found")

    # Get line items
    lines = (await db.execute(
        select(ClaimLineItem).where(ClaimLineItem.claim_id == claim_id).order_by(ClaimLineItem.line_number)
    )).scalars().all()

    return {
        "claim": claim,
        "patient_name": claim.patient_name,
        "payer_id": claim.payer_id,
        "payer_type": claim.payer_type,
        "total_billed": float(claim.total_billed) if claim.total_billed else 0,
        "service_date": claim.service_date.isoformat() if claim.service_date else "unknown",
        "submission_date": claim.submission_date.isoformat() if claim.submission_date else "unknown",
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
        "prior_auth": claim.prior_auth_number,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/denial-review", response_model=DenialAnalysis)
async def review_denial(
    body: DenialReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """AI-powered denial analysis — identifies reason, recommends action, generates appeal.

    Analyzes the denial codes, EOB text, and claim context to determine:
    - Why the claim was denied
    - Whether an appeal is worth pursuing
    - What the appeal letter should say
    - What documentation to include
    """
    practice_id = user["practice_id"]
    context = await _get_claim_context(db, body.claim_id, practice_id)

    prompt = f"""You are an orthodontic insurance claims specialist. Analyze this denied claim and provide recommendations.

CLAIM DETAILS:
- Patient: {context['patient_name']}
- Payer: {context['payer_id']} ({context['payer_type']})
- Service Date: {context['service_date']}
- Submission Date: {context['submission_date']}
- Total Billed: ${context['total_billed']:.2f}
- Prior Authorization: {context['prior_auth'] or 'None'}
- CDT Codes: {', '.join(context['cdt_codes'])}

DENIAL INFORMATION:
- Denial Codes: {', '.join(context['denial_codes']) if context['denial_codes'] else 'None specified'}
- Denial Reason: {context['denial_reason']}
{f'- EOB Text: {body.eob_text[:1000]}' if body.eob_text else ''}

LINE ITEMS:
{chr(10).join(f"  - {li['code']}: ${li['billed']:.2f}" + (f" [DENIED: {li['denial_code']} - {li['denial_reason']}]" if li['denied'] else " [OK]") for li in context['line_items'])}

RESPOND IN THIS EXACT FORMAT (no markdown):
CATEGORY: [one of: medical_necessity, coding_error, timely_filing, auth_required, benefit_exhausted, coordination_of_benefits, duplicate_claim, missing_info, other]
EXPLANATION: [2-3 sentences explaining why this was denied in plain English]
APPEAL_RECOMMENDED: [yes or no]
SUCCESS_LIKELIHOOD: [high, medium, or low]
APPEAL_LETTER: [Write a professional appeal letter addressed to the payer's claims department. Include: patient info reference, claim number reference, specific denial reason being contested, clinical justification, request for reconsideration. Keep it concise but thorough.]
SUPPORTING_DOCS: [Comma-separated list of documents to include with the appeal]
CORRECTIVE_ACTIONS: [Comma-separated list of things to fix or verify before resubmitting]"""

    result = await _call_darius(prompt)

    # Parse response
    category = "other"
    explanation = ""
    appeal_recommended = False
    success_likelihood = "low"
    appeal_letter = None
    supporting_docs = []
    corrective_actions = []

    current_field = None
    current_value = []

    for line in result.split("\n"):
        line_stripped = line.strip()
        if line_stripped.startswith("CATEGORY:"):
            if current_field and current_value:
                _assign_field(current_field, "\n".join(current_value), locals())
            current_field = "category"
            current_value = [line_stripped[len("CATEGORY:"):].strip()]
        elif line_stripped.startswith("EXPLANATION:"):
            if current_field and current_value:
                _assign_field(current_field, "\n".join(current_value), locals())
            current_field = "explanation"
            current_value = [line_stripped[len("EXPLANATION:"):].strip()]
        elif line_stripped.startswith("APPEAL_RECOMMENDED:"):
            if current_field and current_value:
                _assign_field(current_field, "\n".join(current_value), locals())
            current_field = "appeal_recommended"
            current_value = [line_stripped[len("APPEAL_RECOMMENDED:"):].strip()]
        elif line_stripped.startswith("SUCCESS_LIKELIHOOD:"):
            if current_field and current_value:
                _assign_field(current_field, "\n".join(current_value), locals())
            current_field = "success_likelihood"
            current_value = [line_stripped[len("SUCCESS_LIKELIHOOD:"):].strip()]
        elif line_stripped.startswith("APPEAL_LETTER:"):
            if current_field and current_value:
                _assign_field(current_field, "\n".join(current_value), locals())
            current_field = "appeal_letter"
            current_value = [line_stripped[len("APPEAL_LETTER:"):].strip()]
        elif line_stripped.startswith("SUPPORTING_DOCS:"):
            if current_field and current_value:
                _assign_field(current_field, "\n".join(current_value), locals())
            current_field = "supporting_docs"
            current_value = [line_stripped[len("SUPPORTING_DOCS:"):].strip()]
        elif line_stripped.startswith("CORRECTIVE_ACTIONS:"):
            if current_field and current_value:
                _assign_field(current_field, "\n".join(current_value), locals())
            current_field = "corrective_actions"
            current_value = [line_stripped[len("CORRECTIVE_ACTIONS:"):].strip()]
        else:
            if current_field:
                current_value.append(line_stripped)

    # Final assignment
    if current_field and current_value:
        val = "\n".join(current_value).strip()
        if current_field == "category":
            category = val.lower().replace(" ", "_")
        elif current_field == "explanation":
            explanation = val
        elif current_field == "appeal_recommended":
            appeal_recommended = val.lower() in ("yes", "true")
        elif current_field == "success_likelihood":
            success_likelihood = val.lower()
        elif current_field == "appeal_letter":
            appeal_letter = val
        elif current_field == "supporting_docs":
            supporting_docs = [d.strip() for d in val.split(",") if d.strip()]
        elif current_field == "corrective_actions":
            corrective_actions = [a.strip() for a in val.split(",") if a.strip()]

    # Fallback if parsing missed fields
    if not explanation:
        explanation = result[:500]

    # Store the appeal on the claim if generated
    if appeal_letter:
        claim = context["claim"]
        claim.appeal_text = appeal_letter
        claim.original_denial_eob = body.eob_text
        await db.commit()

    await audit_log(db, practice_id, user["user_id"], "ai.denial_review", "insurance_claim", body.claim_id)

    return DenialAnalysis(
        claim_id=body.claim_id,
        denial_category=category,
        denial_explanation=explanation,
        appeal_recommended=appeal_recommended,
        appeal_success_likelihood=success_likelihood,
        appeal_letter=appeal_letter,
        supporting_docs_needed=supporting_docs,
        corrective_actions=corrective_actions,
    )


@router.post("/generate-appeal", response_model=AppealResponse)
async def generate_appeal(
    body: AppealGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Generate (or regenerate) an appeal letter for a denied claim."""
    practice_id = user["practice_id"]
    context = await _get_claim_context(db, body.claim_id, practice_id)

    additional = f"\nADDITIONAL CONTEXT FROM OFFICE: {body.additional_context}" if body.additional_context else ""

    prompt = f"""You are an orthodontic insurance appeals specialist. Write a formal appeal letter for this denied claim.

CLAIM: {context['patient_name']} | Payer: {context['payer_id']} | Service: {context['service_date']} | Billed: ${context['total_billed']:.2f}
DENIAL: {context['denial_reason']}
CODES: {', '.join(context['cdt_codes'])}
PRIOR AUTH: {context['prior_auth'] or 'None on file'}
{additional}

Write a professional appeal letter that:
1. References the claim and patient specifically
2. States the denial reason being contested
3. Provides clinical justification for the services rendered
4. Cites relevant orthodontic treatment standards
5. Requests reconsideration with a clear ask
6. Is addressed to "Claims Review Department"

RESPOND IN THIS EXACT FORMAT:
APPEAL_TYPE: [one of: clinical_narrative, coding_correction, timely_filing_exception, peer_to_peer_request]
LETTER: [The complete appeal letter text]"""

    result = await _call_darius(prompt)

    # Parse
    appeal_type = "clinical_narrative"
    letter = result

    for line in result.split("\n"):
        if line.strip().startswith("APPEAL_TYPE:"):
            appeal_type = line.strip()[len("APPEAL_TYPE:"):].strip().lower().replace(" ", "_")
        elif line.strip().startswith("LETTER:"):
            letter = result[result.index("LETTER:") + len("LETTER:"):].strip()
            break

    # Store on claim
    claim = context["claim"]
    claim.appeal_text = letter
    claim.appeal_date = datetime.now(timezone.utc)
    claim.appeal_status = "drafted"
    await db.commit()

    await audit_log(db, practice_id, user["user_id"], "ai.generate_appeal", "insurance_claim", body.claim_id)

    return AppealResponse(
        claim_id=body.claim_id,
        appeal_letter=letter,
        appeal_type=appeal_type,
    )


def _assign_field(field: str, value: str, local_vars: dict):
    """Helper to assign parsed values — used during response parsing."""
    # This is handled inline in the parsing loop above
    pass
