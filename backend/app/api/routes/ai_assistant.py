import uuid
"""OrthoFlow API — AI Clinical Note Assistant.

Routes clinical note assist requests through Darius for:
- Structured note generation from DA shorthand
- Note completeness checking
- Next-visit suggestions based on treatment history
- Appointment prep briefs

Architecture: OrthoFlow → Darius → LLM (currently Haiku, future: Mistral Small local)
The model selection is handled by Darius config — no code changes needed to swap models.
"""
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.clinical import Patient, Appointment, TreatmentNote, ToothChart

router = APIRouter(prefix="/api/v1/ai", tags=["ai-assistant"])

# Darius endpoint — abstraction layer for LLM calls
# When migrating to Mistral Small, only Darius config changes. This code stays the same.
DARIUS_URL = os.environ.get("DARIUS_URL", "http://darius-agent:8000")


# ── Schemas ───────────────────────────────────────────────────────────────────

class NoteAssistRequest(BaseModel):
    patient_id: str
    raw_input: str = Field(..., min_length=3, max_length=2000, description="DA's rough notes/shorthand")
    appointment_type: str | None = None
    include_next_visit: bool = True


class NoteAssistResponse(BaseModel):
    structured_note: str
    next_visit_suggestion: str | None = None
    completeness_flags: list[str]


class PrepBriefRequest(BaseModel):
    appointment_id: str


class PrepBriefResponse(BaseModel):
    patient_name: str
    treatment_phase: str
    last_visit_summary: str | None
    today_expected: str
    prep_items: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_patient_context(db: AsyncSession, patient_id: str, practice_id: str) -> dict:
    """Gather patient context for the LLM — treatment phase, recent notes, tooth chart."""
    patient = (await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Last 5 notes
    notes_result = await db.execute(
        select(TreatmentNote)
        .where(TreatmentNote.patient_id == patient_id)
        .order_by(TreatmentNote.created_at.desc())
        .limit(5)
    )
    recent_notes = [n.note_text for n in notes_result.scalars().all()]

    # Tooth chart summary
    chart = (await db.execute(
        select(ToothChart).where(ToothChart.patient_id == patient_id)
    )).scalar_one_or_none()

    chart_summary = ""
    if chart:
        chart_summary = f"Upper wire: {chart.upper_wire or 'none'}. Lower wire: {chart.lower_wire or 'none'}."
        if chart.appliances:
            chart_summary += f" Appliances: {', '.join(a.get('name', '') for a in chart.appliances)}."

    return {
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "treatment_phase": patient.treatment_phase or "unknown",
        "recent_notes": recent_notes,
        "chart_summary": chart_summary,
    }


async def _call_darius(task: str) -> str:
    """Call Darius for LLM-powered text generation.
    Uses 'light' model override to get direct Haiku response without
    planning/evaluation (clinical notes don't need multi-step execution).
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DARIUS_URL}/task",
                json={"task": task, "project": "orthoflow-ai", "model_override": "light", "session_id": f"of-{uuid.uuid4().hex[:8]}"},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("args", {}).get("proposal", data.get("result", ""))
    except httpx.TimeoutException:
        raise HTTPException(503, "AI assistant timed out — try again")
    except Exception as e:
        raise HTTPException(503, f"AI assistant unavailable: {str(e)[:100]}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/notes/assist", response_model=NoteAssistResponse)
async def assist_note(
    body: NoteAssistRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """AI-assisted clinical note generation.

    DA provides rough shorthand → returns structured clinical note,
    completeness flags, and optional next-visit suggestion.
    """
    context = await _get_patient_context(db, body.patient_id, user["practice_id"])

    # Build the prompt for Darius
    prompt = f"""You are a clinical note assistant for an orthodontic practice. 
A dental assistant has written rough notes about a patient visit. Convert them into a properly structured clinical note.

PATIENT CONTEXT:
- Name: {context['patient_name']}
- Treatment Phase: {context['treatment_phase']}
- Current Wires/Appliances: {context['chart_summary'] or 'Not documented'}
- Recent Notes: {'; '.join(context['recent_notes'][:3]) if context['recent_notes'] else 'None on file'}
{f'- Appointment Type: {body.appointment_type}' if body.appointment_type else ''}

DA'S RAW INPUT:
{body.raw_input}

RESPOND IN THIS EXACT FORMAT (no markdown, no extra text):
STRUCTURED_NOTE: [Write the full clinical note in proper orthodontic documentation format. Include: Procedure, Findings, Patient Compliance, Archwire/Appliance Changes, and Next Steps.]
NEXT_VISIT: [One sentence suggesting what to plan for next visit based on the note content and treatment phase]
MISSING: [Comma-separated list of any important clinical details that seem missing from the DA's input, or NONE if complete]"""

    result = await _call_darius(prompt)

    # Parse the structured response
    structured_note = ""
    next_visit = None
    completeness_flags = []

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("STRUCTURED_NOTE:"):
            structured_note = line[len("STRUCTURED_NOTE:"):].strip()
        elif line.startswith("NEXT_VISIT:"):
            next_visit = line[len("NEXT_VISIT:"):].strip()
        elif line.startswith("MISSING:"):
            missing = line[len("MISSING:"):].strip()
            if missing and missing.upper() != "NONE":
                completeness_flags = [f.strip() for f in missing.split(",") if f.strip()]

    # Fallback: if parsing failed, use the full response as the note
    if not structured_note:
        structured_note = result.strip()

    await audit_log(db, user["practice_id"], user["user_id"], "ai.note_assist", "patient", body.patient_id)

    return NoteAssistResponse(
        structured_note=structured_note,
        next_visit_suggestion=next_visit if body.include_next_visit else None,
        completeness_flags=completeness_flags,
    )


@router.post("/appointments/prep", response_model=PrepBriefResponse)
async def appointment_prep_brief(
    body: PrepBriefRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Generate a prep brief for an upcoming appointment.

    Tells the DA: who's coming, what phase they're in, what was done last time,
    and what to have ready.
    """
    # Get appointment
    appt = (await db.execute(
        select(Appointment).where(
            Appointment.id == body.appointment_id,
            Appointment.practice_id == user["practice_id"],
        )
    )).scalar_one_or_none()
    if not appt:
        raise HTTPException(404, "Appointment not found")

    context = await _get_patient_context(db, str(appt.patient_id), user["practice_id"])

    last_note_summary = context["recent_notes"][0][:200] if context["recent_notes"] else None

    # Build prompt for prep brief
    prompt = f"""You are a clinical prep assistant for an orthodontic practice.
Generate a brief prep summary for a dental assistant before a patient appointment.

PATIENT: {context['patient_name']}
TREATMENT PHASE: {context['treatment_phase']}
APPOINTMENT TYPE: {appt.appointment_type or 'General'}
CURRENT WIRES: {context['chart_summary'] or 'Not documented'}
LAST VISIT NOTE: {last_note_summary or 'No previous notes'}

RESPOND IN THIS EXACT FORMAT (no markdown, no extra text):
TODAY_EXPECTED: [One sentence on what will likely happen today based on treatment phase and last visit]
PREP_ITEMS: [Comma-separated list of supplies/instruments to have ready]"""

    result = await _call_darius(prompt)

    # Parse
    today_expected = appt.appointment_type or "General appointment"
    prep_items = []

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("TODAY_EXPECTED:"):
            today_expected = line[len("TODAY_EXPECTED:"):].strip()
        elif line.startswith("PREP_ITEMS:"):
            items = line[len("PREP_ITEMS:"):].strip()
            prep_items = [i.strip() for i in items.split(",") if i.strip()]

    await audit_log(db, user["practice_id"], user["user_id"], "ai.prep_brief", "appointment", body.appointment_id)

    return PrepBriefResponse(
        patient_name=context["patient_name"],
        treatment_phase=context["treatment_phase"],
        last_visit_summary=last_note_summary,
        today_expected=today_expected,
        prep_items=prep_items,
    )
