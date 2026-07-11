"""OrthoFlow API — AI Referral Letter Generation & Imaging Reasoning.

Routes referral intelligence requests through Darius for:
- Professional referral letter auto-generation with patient context
- Imaging reasoning — explains WHY overdue radiographs are needed
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
from app.models.clinical import Patient, TreatmentNote, ToothChart
from app.models.imaging import PatientImage, ImagingAlert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai/referrals", tags=["ai-referrals"])

DARIUS_URL = os.environ.get("DARIUS_URL", "http://darius-agent:8000")


# ── Schemas ───────────────────────────────────────────────────────────────────


class ReferralTo(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    specialty: str = Field(..., min_length=1, max_length=100)
    address: str | None = None


class GenerateLetterRequest(BaseModel):
    patient_id: str
    referral_to: ReferralTo
    reason_for_referral: str = Field(..., min_length=5, max_length=1000)
    urgency: str = Field(default="routine", pattern="^(routine|urgent|emergent)$")


class GenerateLetterResponse(BaseModel):
    letter_text: str
    letter_type: str  # referral, consultation_request, transfer_of_care


class ImagingReasoningRequest(BaseModel):
    alert_id: str


class ImagingReasoningResponse(BaseModel):
    reasoning: str
    clinical_guidelines: list[str]
    recommended_views: list[str]
    urgency_level: str  # routine, soon, urgent


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _call_darius(task: str) -> str:
    """Call Darius for LLM-powered text generation."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DARIUS_URL}/task",
                json={"task": task, "project": "orthoflow-ai"},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("args", {}).get("proposal", "")
    except httpx.TimeoutException:
        logger.error("darius_timeout_referrals")
        raise HTTPException(503, "AI referral service timed out — try again")
    except httpx.HTTPStatusError as e:
        logger.error("darius_http_error", extra={"status": e.response.status_code})
        raise HTTPException(503, "AI referral service unavailable")
    except Exception as e:
        logger.error("darius_error", extra={"error": str(e)[:200]})
        raise HTTPException(503, f"AI referral service error: {str(e)[:100]}")


async def _get_patient_context_for_referral(
    db: AsyncSession, patient_id: str, practice_id: str
) -> dict:
    """Gather patient context specifically for referral letter generation."""
    patient = (
        await db.execute(
            select(Patient).where(
                Patient.id == patient_id, Patient.practice_id == practice_id
            )
        )
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Recent treatment notes (last 10)
    notes = (
        await db.execute(
            select(TreatmentNote)
            .where(TreatmentNote.patient_id == patient_id)
            .order_by(TreatmentNote.created_at.desc())
            .limit(10)
        )
    ).scalars().all()

    # Tooth chart
    chart = (
        await db.execute(
            select(ToothChart).where(ToothChart.patient_id == patient_id)
        )
    ).scalar_one_or_none()

    # Recent imaging dates
    images = (
        await db.execute(
            select(PatientImage)
            .where(PatientImage.patient_id == patient_id)
            .order_by(PatientImage.captured_date.desc())
            .limit(10)
        )
    ).scalars().all()

    chart_summary = ""
    if chart:
        parts = []
        if chart.upper_wire:
            parts.append(f"Upper wire: {chart.upper_wire}")
        if chart.lower_wire:
            parts.append(f"Lower wire: {chart.lower_wire}")
        if chart.appliances:
            appliance_names = [a.get("type", "") for a in chart.appliances if isinstance(a, dict)]
            if appliance_names:
                parts.append(f"Appliances: {', '.join(appliance_names)}")
        chart_summary = "; ".join(parts)

    notes_summary = "\n".join(
        f"  [{n.created_at.strftime('%Y-%m-%d')}] {n.note_text[:150]}" for n in notes[:5]
    )

    imaging_dates = [
        f"{img.image_type}: {img.captured_date.isoformat()}" for img in images[:5]
    ]

    return {
        "patient": patient,
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "dob": patient.date_of_birth.isoformat() if patient.date_of_birth else "Unknown",
        "treatment_phase": patient.treatment_phase or "unknown",
        "chart_summary": chart_summary or "Not documented",
        "notes_summary": notes_summary or "No recent notes",
        "imaging_dates": imaging_dates,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/generate-letter", response_model=GenerateLetterResponse)
async def generate_referral_letter(
    body: GenerateLetterRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Generate a professional referral letter for a patient.

    Includes patient summary, treatment history, relevant imaging dates,
    reason for referral, and urgency level.
    """
    practice_id = user["practice_id"]
    context = await _get_patient_context_for_referral(db, body.patient_id, practice_id)

    imaging_text = ", ".join(context["imaging_dates"]) if context["imaging_dates"] else "No imaging on file"

    prompt = f"""You are a clinical letter writer for an orthodontic practice.
Generate a professional referral letter to send to another provider.

REFERRING PRACTICE: OrthoFlow Orthodontics

PATIENT INFORMATION:
- Name: {context['patient_name']}
- DOB: {context['dob']}
- Treatment Phase: {context['treatment_phase']}
- Current Orthodontic Status: {context['chart_summary']}

RECENT TREATMENT NOTES:
{context['notes_summary']}

RELEVANT IMAGING:
{imaging_text}

REFERRAL DETAILS:
- Referred To: {body.referral_to.name}, {body.referral_to.specialty}
{f'- Address: {body.referral_to.address}' if body.referral_to.address else ''}
- Reason for Referral: {body.reason_for_referral}
- Urgency: {body.urgency}

RESPOND IN THIS EXACT FORMAT (no markdown):
LETTER_TYPE: [one of: referral, consultation_request, transfer_of_care]
LETTER_TEXT: [Write the complete professional referral letter. Include:
- Date and letterhead placeholder
- Provider greeting
- Patient identification paragraph
- Treatment history summary (concise)
- Specific reason for referral with clinical context
- Relevant imaging and records being sent
- Urgency and requested timeline
- Professional closing with callback number placeholder
Keep it professional, concise, and clinically relevant.]"""

    result = await _call_darius(prompt)

    # Parse response
    letter_type = "referral"
    letter_text = ""

    lines = result.split("\n")
    letter_start_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("LETTER_TYPE:"):
            raw_type = stripped[len("LETTER_TYPE:"):].strip().lower().replace(" ", "_")
            if raw_type in ("referral", "consultation_request", "transfer_of_care"):
                letter_type = raw_type
        elif stripped.startswith("LETTER_TEXT:"):
            letter_start_idx = i
            # Get content after the label on the same line
            first_line = stripped[len("LETTER_TEXT:"):].strip()
            remaining_lines = [first_line] if first_line else []
            remaining_lines.extend(l.rstrip() for l in lines[i + 1:])
            letter_text = "\n".join(remaining_lines).strip()
            break

    # Fallback if parsing failed
    if not letter_text:
        letter_text = result.strip()

    await audit_log(
        db, practice_id, user["user_id"], "ai.generate_referral_letter", "patient",
        body.patient_id,
        details=f"Referral to {body.referral_to.name} ({body.referral_to.specialty})",
    )

    return GenerateLetterResponse(
        letter_text=letter_text,
        letter_type=letter_type,
    )


@router.post("/imaging-reasoning/{patient_id}", response_model=ImagingReasoningResponse)
async def imaging_reasoning(
    patient_id: str,
    body: ImagingReasoningRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Explain WHY an overdue imaging alert requires action.

    For a specific imaging alert, provides clinical reasoning including:
    guidelines cited, what to look for, and impact of delaying.
    """
    practice_id = user["practice_id"]

    # Verify patient belongs to practice
    patient = (
        await db.execute(
            select(Patient).where(
                Patient.id == patient_id, Patient.practice_id == practice_id
            )
        )
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Fetch the imaging alert
    alert = (
        await db.execute(
            select(ImagingAlert).where(
                ImagingAlert.id == body.alert_id,
                ImagingAlert.patient_id == patient_id,
                ImagingAlert.practice_id == practice_id,
            )
        )
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Imaging alert not found")

    # Get last image of this type
    last_image = (
        await db.execute(
            select(PatientImage)
            .where(
                PatientImage.patient_id == patient_id,
                PatientImage.image_type == alert.image_type,
            )
            .order_by(PatientImage.captured_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    last_taken_info = (
        f"Last {alert.image_type} taken: {last_image.captured_date.isoformat()}"
        if last_image
        else f"No previous {alert.image_type} on file"
    )

    # Tooth chart for context
    chart = (
        await db.execute(
            select(ToothChart).where(ToothChart.patient_id == patient_id)
        )
    ).scalar_one_or_none()

    chart_summary = ""
    if chart:
        parts = []
        if chart.upper_wire:
            parts.append(f"Upper wire: {chart.upper_wire}")
        if chart.lower_wire:
            parts.append(f"Lower wire: {chart.lower_wire}")
        chart_summary = "; ".join(parts) if parts else "Chart exists"

    prompt = f"""You are a clinical imaging advisor for an orthodontic practice.
Explain WHY this overdue imaging is needed based on clinical guidelines.

PATIENT: {patient.first_name} {patient.last_name}
TREATMENT PHASE: {patient.treatment_phase or 'unknown'}
ORTHODONTIC STATUS: {chart_summary or 'Not documented'}

IMAGING ALERT:
- Image Type: {alert.image_type}
- Due Date: {alert.due_date.isoformat()}
- {last_taken_info}
- Rule: {alert.rule_description or 'Standard interval'}
- Treatment Phase at Alert: {alert.treatment_phase or patient.treatment_phase or 'unknown'}

RESPOND IN THIS EXACT FORMAT (no markdown):
REASONING: [2-4 sentences explaining why this image is clinically needed at this point in treatment. Be specific to the image type and treatment phase.]
CLINICAL_GUIDELINES: [Pipe-separated list of relevant clinical guidelines or standards, e.g. "AAO recommends panoramic every 12-18 months during active treatment|ADA guidelines for periapical imaging during root movement|Standard of care for monitoring root resorption"]
RECOMMENDED_VIEWS: [Comma-separated list of specific views/images to take, e.g. "Panoramic radiograph, Lateral cephalogram"]
URGENCY_LEVEL: [one of: routine, soon, urgent]"""

    result = await _call_darius(prompt)

    # Parse response
    reasoning = ""
    clinical_guidelines: list[str] = []
    recommended_views: list[str] = []
    urgency_level = "routine"

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("REASONING:"):
            reasoning = line[len("REASONING:"):].strip()
        elif line.startswith("CLINICAL_GUIDELINES:"):
            raw = line[len("CLINICAL_GUIDELINES:"):].strip()
            clinical_guidelines = [g.strip() for g in raw.split("|") if g.strip()]
        elif line.startswith("RECOMMENDED_VIEWS:"):
            raw = line[len("RECOMMENDED_VIEWS:"):].strip()
            recommended_views = [v.strip() for v in raw.split(",") if v.strip()]
        elif line.startswith("URGENCY_LEVEL:"):
            raw = line[len("URGENCY_LEVEL:"):].strip().lower()
            if raw in ("routine", "soon", "urgent"):
                urgency_level = raw

    # Fallbacks
    if not reasoning:
        reasoning = f"{alert.image_type} imaging is overdue based on standard treatment intervals."
    if not clinical_guidelines:
        clinical_guidelines = ["Standard orthodontic imaging guidelines apply"]
    if not recommended_views:
        recommended_views = [alert.image_type]

    await audit_log(
        db, practice_id, user["user_id"], "ai.imaging_reasoning", "imaging_alert",
        body.alert_id,
        details=f"Patient {patient_id}, image type: {alert.image_type}",
    )

    return ImagingReasoningResponse(
        reasoning=reasoning,
        clinical_guidelines=clinical_guidelines,
        recommended_views=recommended_views,
        urgency_level=urgency_level,
    )
