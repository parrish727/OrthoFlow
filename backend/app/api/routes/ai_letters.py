"""OrthoFlow API — Multi-type AI Letters.

Generates several letter types (school note, referral, Medicaid, 30/60/90-day collections,
thank-you referral) and offers Gmail-style AI "polish" (rewrite in a chosen tone). Learns each
doctor's wording over time by injecting their saved samples as FEW-SHOT examples — prompt-time
personalization, NOT model fine-tuning. Anthropic Claude only.
"""
import logging
import httpx
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import get_db
from app.models.clinical import Patient
from app.models.ortho_ops import DoctorLetterStyle

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai/letters", tags=["ai-letters"])

LETTER_TYPES = {
    "school": "a school absence/excuse note confirming the patient had an orthodontic appointment",
    "referral": "a professional referral letter to another provider",
    "medicaid": "a Medicaid medical-necessity letter supporting orthodontic treatment",
    "collections_30": "a friendly 30-day past-due balance reminder letter",
    "collections_60": "a firmer 60-day past-due collections letter",
    "collections_90": "a final 90-day collections notice letter",
    "thank_you_referral": "a warm thank-you letter to a referring source for sending a patient",
    "general": "a general professional letter",
}


class GenerateRequest(BaseModel):
    patient_id: str | None = None
    letter_type: str = Field(..., pattern="^(school|referral|medicaid|collections_30|collections_60|collections_90|thank_you_referral|general)$")
    context: str = Field("", max_length=2000)
    tone: str = Field("professional", pattern="^(professional|warm|firm|concise)$")


class PolishRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=6000)
    tone: str = Field("professional", pattern="^(professional|warm|firm|concise|shorter|friendlier)$")
    letter_type: str = "general"


class SaveStyleRequest(BaseModel):
    letter_type: str = Field(..., max_length=40)
    sample_text: str = Field(..., min_length=20, max_length=6000)
    tone: str | None = None


async def _call_claude(prompt: str) -> str:
    """Anthropic Claude text generation (approved provider only)."""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(503, "AI is not configured")
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
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
    except httpx.TimeoutException:
        raise HTTPException(503, "AI request timed out")
    except Exception as e:
        logger.error("ai_letters_error", extra={"error": str(e)[:200]})
        raise HTTPException(503, f"AI letter service error: {str(e)[:100]}")


async def _style_examples(db: AsyncSession, practice_id, user_id, letter_type: str) -> str:
    """Few-shot: pull this doctor's saved samples (same type preferred) to steer wording."""
    rows = (await db.execute(
        select(DoctorLetterStyle).where(
            DoctorLetterStyle.practice_id == practice_id,
            DoctorLetterStyle.user_id == user_id,
        ).order_by(DoctorLetterStyle.letter_type == letter_type, DoctorLetterStyle.use_count.desc()).limit(3)
    )).scalars().all()
    if not rows:
        return ""
    blocks = "\n\n".join(f"EXAMPLE ({r.letter_type}):\n{r.sample_text}" for r in rows)
    return ("\n\nMatch this provider's personal writing style, using these prior letters as "
            f"style references (mimic tone/phrasing, NOT content):\n{blocks}")


@router.get("/types")
async def list_letter_types(user: dict = Depends(get_current_user)):
    return {"types": [{"key": k, "description": v} for k, v in LETTER_TYPES.items()]}


@router.post("/generate")
async def generate_letter(
    body: GenerateRequest, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Generate a letter of the requested type, personalized to the doctor's style (few-shot)."""
    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]

    patient_name = "the patient"
    if body.patient_id:
        p = (await db.execute(select(Patient).where(Patient.id == UUID(body.patient_id), Patient.practice_id == practice_id))).scalar_one_or_none()
        if p:
            patient_name = f"{p.first_name} {p.last_name}"

    style = await _style_examples(db, practice_id, UUID(user["user_id"]) if isinstance(user["user_id"], str) else user["user_id"], body.letter_type)
    desc = LETTER_TYPES.get(body.letter_type, LETTER_TYPES["general"])
    prompt = (
        f"You are drafting {desc} for an orthodontic practice. Patient: {patient_name}. "
        f"Tone: {body.tone}. Additional context: {body.context or 'none'}. "
        f"Write a complete, ready-to-send letter with appropriate salutation and closing. "
        f"Use bracketed placeholders like [Practice Name] where specifics are unknown."
        f"{style}"
    )
    text = await _call_claude(prompt)
    await audit_log(db, practice_id, user["user_id"], "ai_letter.generate", "letter", body.letter_type)
    return {"letter_type": body.letter_type, "tone": body.tone, "letter_text": text, "personalized": bool(style)}


@router.post("/polish")
async def polish_letter(
    body: PolishRequest, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Gmail-style AI polish — rewrite the given text in the chosen tone, keeping meaning."""
    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    prompt = (
        f"Rewrite the following letter to be more {body.tone}, preserving all facts and intent. "
        f"Return only the rewritten letter.\n\n{body.text}"
    )
    text = await _call_claude(prompt)
    await audit_log(db, practice_id, user["user_id"], "ai_letter.polish", "letter", body.tone)
    return {"tone": body.tone, "letter_text": text}


@router.post("/save-style", status_code=201)
async def save_style(
    body: SaveStyleRequest, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """Save a sample of the doctor's writing so AI learns their style over time (few-shot)."""
    practice_id = UUID(user["practice_id"]) if isinstance(user["practice_id"], str) else user["practice_id"]
    row = DoctorLetterStyle(
        practice_id=practice_id,
        user_id=UUID(user["user_id"]) if isinstance(user["user_id"], str) else user["user_id"],
        letter_type=body.letter_type, sample_text=body.sample_text, tone=body.tone,
    )
    db.add(row)
    await db.commit()
    await audit_log(db, practice_id, user["user_id"], "ai_letter.save_style", "letter_style", body.letter_type)
    return {"id": str(row.id), "letter_type": body.letter_type, "saved": True}
