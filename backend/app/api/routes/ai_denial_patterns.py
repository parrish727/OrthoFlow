import uuid
"""OrthoFlow API — AI Denial Pattern Detection.

Analyzes denied claims across the practice to identify systemic patterns:
- Same payer denying same codes repeatedly
- Coding issues across multiple claims
- Revenue recovery opportunities
- Per-payer and batch denial analysis via Darius
"""
import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.claims import InsuranceClaim
from app.models.finance import ClaimLineItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai/denial-patterns", tags=["ai-denial-patterns"])



# ── Schemas ───────────────────────────────────────────────────────────────────


class DenialPattern(BaseModel):
    payer_id: str
    cdt_code: str | None = None
    denial_reason: str
    count: int
    total_amount: float
    recommendation: str


class DenialAnalyzeResponse(BaseModel):
    patterns: list[DenialPattern]
    recommendations: list[str]
    total_denied_amount: float
    recovery_potential: float


class PayerDenialResponse(BaseModel):
    payer_id: str
    patterns: list[DenialPattern]
    recommendations: list[str]
    total_denied_amount: float
    denial_rate: float
    top_denied_codes: list[str]


class BatchClaimReviewRequest(BaseModel):
    claim_ids: list[str] = Field(..., min_length=1, max_length=50)


class ClaimDenialInsight(BaseModel):
    claim_id: str
    denial_category: str
    explanation: str
    appeal_recommended: bool
    recovery_likelihood: str  # high, medium, low


class BatchReviewResponse(BaseModel):
    claim_insights: list[ClaimDenialInsight]
    practice_summary: str
    total_denied: float
    estimated_recoverable: float


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _call_darius(task: str) -> str:
    """Call Anthropic Claude directly for text generation."""
    from app.core.config import settings
    try:
        async with httpx.AsyncClient() as client:
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
                    "messages": [{"role": "user", "content": task}],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]
    except httpx.TimeoutException:
        raise HTTPException(503, "Request timed out")
    except Exception as e:
        raise HTTPException(503, f"Service unavailable: {str(e)[:100]}")
    except httpx.HTTPStatusError as e:
        logger.error("darius_http_error", extra={"status": e.response.status_code})
        raise HTTPException(503, "AI analysis service unavailable")
    except Exception as e:
        logger.error("darius_error", extra={"error": str(e)[:200]})
        raise HTTPException(503, f"AI analysis service error: {str(e)[:100]}")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/analyze", response_model=DenialAnalyzeResponse)
async def analyze_denial_patterns(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Analyze all denied claims for the practice to identify systemic patterns.

    Groups denials by payer, by code, and by reason. Provides AI-generated
    recommendations for improving claim acceptance rates.
    """
    practice_id = user["practice_id"]

    # Fetch all denied claims for the practice
    denied_claims = (
        await db.execute(
            select(InsuranceClaim).where(
                InsuranceClaim.practice_id == practice_id,
                InsuranceClaim.status == "denied",
            )
        )
    ).scalars().all()

    if not denied_claims:
        return DenialAnalyzeResponse(
            patterns=[],
            recommendations=["No denied claims found — great job!"],
            total_denied_amount=0.0,
            recovery_potential=0.0,
        )

    total_denied = sum(float(c.total_billed or 0) for c in denied_claims)

    # Group by payer + denial reason
    payer_reason_groups: dict[tuple[str, str], list[InsuranceClaim]] = {}
    code_groups: dict[str, list[InsuranceClaim]] = {}

    for claim in denied_claims:
        reason = claim.denial_reason or "Unspecified"
        key = (claim.payer_id, reason)
        payer_reason_groups.setdefault(key, []).append(claim)

        # Group by CDT codes
        if claim.cdt_codes:
            codes = claim.cdt_codes if isinstance(claim.cdt_codes, list) else []
            for code in codes:
                if isinstance(code, str):
                    code_groups.setdefault(code, []).append(claim)

    # Build pattern summary for Darius
    pattern_lines: list[str] = []
    raw_patterns: list[dict] = []

    for (payer_id, reason), claims in sorted(
        payer_reason_groups.items(), key=lambda x: len(x[1]), reverse=True
    )[:20]:
        amount = sum(float(c.total_billed or 0) for c in claims)
        pattern_lines.append(
            f"Payer: {payer_id} | Reason: {reason} | Count: {len(claims)} | Amount: ${amount:.2f}"
        )
        raw_patterns.append({
            "payer_id": payer_id,
            "denial_reason": reason,
            "count": len(claims),
            "total_amount": amount,
        })

    top_codes = sorted(code_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    code_lines = [f"Code {code}: {len(claims)} denials" for code, claims in top_codes]

    prompt = f"""You are an orthodontic insurance claims analyst. Analyze these denial patterns and provide actionable recommendations.

PRACTICE DENIAL SUMMARY:
- Total denied claims: {len(denied_claims)}
- Total denied amount: ${total_denied:.2f}

TOP DENIAL PATTERNS (by payer + reason):
{chr(10).join(pattern_lines)}

TOP DENIED CDT CODES:
{chr(10).join(code_lines)}

RESPOND IN THIS EXACT FORMAT (no markdown):
RECOMMENDATIONS: [Pipe-separated list of 3-5 specific actionable recommendations, e.g. "Submit narratives with D8080 for Delta Dental|Pre-authorize all Class II cases with Cigna|Appeal timely filing denials from MetLife within 30 days"]
RECOVERY_POTENTIAL_PCT: [Integer 0-100 representing what percentage of denied dollars could potentially be recovered with proper action]"""

    result = await _call_darius(prompt)

    # Parse Darius response
    recommendations: list[str] = []
    recovery_pct = 30  # default conservative estimate

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("RECOMMENDATIONS:"):
            raw = line[len("RECOMMENDATIONS:"):].strip()
            recommendations = [r.strip() for r in raw.split("|") if r.strip()]
        elif line.startswith("RECOVERY_POTENTIAL_PCT:"):
            raw = line[len("RECOVERY_POTENTIAL_PCT:"):].strip()
            try:
                recovery_pct = min(100, max(0, int("".join(c for c in raw if c.isdigit()) or "30")))
            except ValueError:
                recovery_pct = 30

    # Build pattern response objects
    patterns: list[DenialPattern] = []
    for item in raw_patterns[:15]:
        # Find top code for this payer pattern
        top_code = None
        for code, claims in top_codes:
            if any(c.payer_id == item["payer_id"] for c in claims):
                top_code = code
                break

        patterns.append(
            DenialPattern(
                payer_id=item["payer_id"],
                cdt_code=top_code,
                denial_reason=item["denial_reason"],
                count=item["count"],
                total_amount=item["total_amount"],
                recommendation=recommendations[0] if recommendations else "Review and appeal",
            )
        )

    recovery_potential = total_denied * (recovery_pct / 100.0)

    if not recommendations:
        recommendations = ["Review denied claims and consider appealing within filing deadlines"]

    await audit_log(
        db, practice_id, user["user_id"], "ai.denial_pattern_analysis", "insurance_claim",
        details=f"Analyzed {len(denied_claims)} denied claims",
    )

    return DenialAnalyzeResponse(
        patterns=patterns,
        recommendations=recommendations,
        total_denied_amount=total_denied,
        recovery_potential=recovery_potential,
    )


@router.get("/payer/{payer_id}", response_model=PayerDenialResponse)
async def payer_denial_patterns(
    payer_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Analyze denial patterns for a specific payer.

    Shows denial rate, top denied codes, and AI-generated recommendations
    specific to this payer's denial behavior.
    """
    practice_id = user["practice_id"]

    # All claims for this payer
    all_payer_claims = (
        await db.execute(
            select(InsuranceClaim).where(
                InsuranceClaim.practice_id == practice_id,
                InsuranceClaim.payer_id == payer_id,
            )
        )
    ).scalars().all()

    if not all_payer_claims:
        raise HTTPException(404, f"No claims found for payer {payer_id}")

    denied_claims = [c for c in all_payer_claims if c.status == "denied"]
    total_claims = len(all_payer_claims)
    denial_rate = len(denied_claims) / total_claims if total_claims > 0 else 0.0
    total_denied = sum(float(c.total_billed or 0) for c in denied_claims)

    if not denied_claims:
        return PayerDenialResponse(
            payer_id=payer_id,
            patterns=[],
            recommendations=[f"No denials from this payer — {total_claims} claims all accepted/paid."],
            total_denied_amount=0.0,
            denial_rate=0.0,
            top_denied_codes=[],
        )

    # Get line items for denied claims to find code patterns
    denied_claim_ids = [c.id for c in denied_claims]
    denied_lines = (
        await db.execute(
            select(ClaimLineItem).where(
                ClaimLineItem.claim_id.in_(denied_claim_ids)
            )
        )
    ).scalars().all()

    # Group denied line items by code
    code_denial_counts: dict[str, int] = {}
    for li in denied_lines:
        if li.denial_code:
            code_denial_counts[li.cdt_code] = code_denial_counts.get(li.cdt_code, 0) + 1

    top_denied_codes = sorted(code_denial_counts.keys(), key=lambda k: code_denial_counts[k], reverse=True)[:10]

    # Group by reason
    reason_groups: dict[str, list[InsuranceClaim]] = {}
    for claim in denied_claims:
        reason = claim.denial_reason or "Unspecified"
        reason_groups.setdefault(reason, []).append(claim)

    reason_lines = [
        f"Reason: {reason} | Count: {len(claims)} | Amount: ${sum(float(c.total_billed or 0) for c in claims):.2f}"
        for reason, claims in sorted(reason_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    ]
    code_lines = [f"{code}: {code_denial_counts[code]} line denials" for code in top_denied_codes[:10]]

    prompt = f"""You are an orthodontic insurance claims analyst. Analyze denial patterns for this specific payer.

PAYER: {payer_id}
TOTAL CLAIMS: {total_claims}
DENIED CLAIMS: {len(denied_claims)}
DENIAL RATE: {denial_rate:.1%}
TOTAL DENIED AMOUNT: ${total_denied:.2f}

DENIAL REASONS:
{chr(10).join(reason_lines)}

TOP DENIED CODES:
{chr(10).join(code_lines)}

RESPOND IN THIS EXACT FORMAT (no markdown):
RECOMMENDATIONS: [Pipe-separated list of 3-5 payer-specific recommendations]"""

    result = await _call_darius(prompt)

    recommendations: list[str] = []
    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("RECOMMENDATIONS:"):
            raw = line[len("RECOMMENDATIONS:"):].strip()
            recommendations = [r.strip() for r in raw.split("|") if r.strip()]

    if not recommendations:
        recommendations = [f"Review denial reasons from {payer_id} and address common issues"]

    # Build patterns
    patterns: list[DenialPattern] = []
    for reason, claims in sorted(reason_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        amount = sum(float(c.total_billed or 0) for c in claims)
        patterns.append(
            DenialPattern(
                payer_id=payer_id,
                cdt_code=top_denied_codes[0] if top_denied_codes else None,
                denial_reason=reason,
                count=len(claims),
                total_amount=amount,
                recommendation=recommendations[0] if recommendations else "Review and appeal",
            )
        )

    await audit_log(
        db, practice_id, user["user_id"], "ai.payer_denial_analysis", "insurance_claim",
        details=f"Payer {payer_id}: {len(denied_claims)} denials analyzed",
    )

    return PayerDenialResponse(
        payer_id=payer_id,
        patterns=patterns,
        recommendations=recommendations,
        total_denied_amount=total_denied,
        denial_rate=denial_rate,
        top_denied_codes=top_denied_codes,
    )


@router.post("/batch-review", response_model=BatchReviewResponse)
async def batch_review_claims(
    body: BatchClaimReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Batch-review multiple denied claims via Darius.

    Returns per-claim denial analysis and a practice-wide summary with
    estimated recoverable amounts.
    """
    practice_id = user["practice_id"]

    # Fetch all requested claims scoped to practice
    claims = (
        await db.execute(
            select(InsuranceClaim).where(
                InsuranceClaim.practice_id == practice_id,
                InsuranceClaim.id.in_(body.claim_ids),
            )
        )
    ).scalars().all()

    if not claims:
        raise HTTPException(400, "No valid claims found for the provided IDs")

    # Build context for Darius
    claim_lines: list[str] = []
    valid_claims: list[InsuranceClaim] = []

    for claim in claims:
        valid_claims.append(claim)
        claim_lines.append(
            f"CLAIM:{claim.id} | Payer:{claim.payer_id} | Codes:{claim.cdt_codes} | "
            f"Billed:${float(claim.total_billed):.2f} | Status:{claim.status} | "
            f"Denial:{claim.denial_reason or 'N/A'}"
        )

    total_denied = sum(
        float(c.total_billed or 0) for c in valid_claims if c.status == "denied"
    )

    prompt = f"""You are an orthodontic insurance claims analyst. Review these claims and provide denial analysis for each.

CLAIMS TO REVIEW:
{chr(10).join(claim_lines)}

RESPOND IN THIS EXACT FORMAT (no markdown):
For each claim, output one line:
CLAIM_INSIGHT: [claim_id] | [category: medical_necessity/coding_error/timely_filing/auth_required/benefit_exhausted/other] | [brief explanation max 100 chars] | [appeal_recommended: yes/no] | [recovery_likelihood: high/medium/low]

After all claims, output:
PRACTICE_SUMMARY: [2-3 sentences summarizing the overall denial situation and top recommended action]
RECOVERABLE_PCT: [Integer 0-100 of estimated recoverable percentage]"""

    result = await _call_darius(prompt)

    # Parse response
    claim_insights: list[ClaimDenialInsight] = []
    practice_summary = ""
    recoverable_pct = 30
    parsed_ids: set[str] = set()

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("CLAIM_INSIGHT:"):
            parts = line[len("CLAIM_INSIGHT:"):].strip().split("|")
            if len(parts) >= 5:
                cid = parts[0].strip()
                # Match to valid claim IDs
                matched_id = None
                for vc in valid_claims:
                    str_id = str(vc.id)
                    if str_id == cid or str_id.startswith(cid[:8]):
                        matched_id = str_id
                        break
                if matched_id and matched_id not in parsed_ids:
                    parsed_ids.add(matched_id)
                    appeal = parts[3].strip().lower() in ("yes", "true")
                    likelihood = parts[4].strip().lower()
                    if likelihood not in ("high", "medium", "low"):
                        likelihood = "medium"
                    claim_insights.append(
                        ClaimDenialInsight(
                            claim_id=matched_id,
                            denial_category=parts[1].strip(),
                            explanation=parts[2].strip()[:200],
                            appeal_recommended=appeal,
                            recovery_likelihood=likelihood,
                        )
                    )
        elif line.startswith("PRACTICE_SUMMARY:"):
            practice_summary = line[len("PRACTICE_SUMMARY:"):].strip()
        elif line.startswith("RECOVERABLE_PCT:"):
            raw = line[len("RECOVERABLE_PCT:"):].strip()
            try:
                recoverable_pct = min(100, max(0, int("".join(c for c in raw if c.isdigit()) or "30")))
            except ValueError:
                recoverable_pct = 30

    # Fill in any claims not parsed
    for vc in valid_claims:
        str_id = str(vc.id)
        if str_id not in parsed_ids:
            claim_insights.append(
                ClaimDenialInsight(
                    claim_id=str_id,
                    denial_category="other",
                    explanation=vc.denial_reason or "Unable to analyze",
                    appeal_recommended=vc.status == "denied",
                    recovery_likelihood="medium",
                )
            )

    if not practice_summary:
        practice_summary = f"Reviewed {len(valid_claims)} claims. {len([c for c in valid_claims if c.status == 'denied'])} are denied."

    estimated_recoverable = total_denied * (recoverable_pct / 100.0)

    await audit_log(
        db, practice_id, user["user_id"], "ai.batch_denial_review", "insurance_claim",
        details=f"Batch reviewed {len(valid_claims)} claims",
    )

    return BatchReviewResponse(
        claim_insights=claim_insights,
        practice_summary=practice_summary,
        total_denied=total_denied,
        estimated_recoverable=estimated_recoverable,
    )
