"""OrthoFlow API — AI Intelligence Layer: Clinical Summarization & Next-Visit Suggestions.

Routes clinical intelligence requests through Darius for:
- Treatment note summarization (last 20 notes → structured history)
- Next-visit procedure suggestions based on treatment context
- Batch patient insights for morning huddle prep
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
from app.models.clinical import Patient, Appointment, TreatmentNote, ToothChart

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai/intelligence", tags=["ai-intelligence"])

DARIUS_URL = os.environ.get("DARIUS_URL", "http://darius-agent:8000")


# ── Schemas ───────────────────────────────────────────────────────────────────


class SummarizeResponse(BaseModel):
    treatment_summary: str
    key_milestones: list[str]
    current_status: str


class NextVisitResponse(BaseModel):
    suggested_procedures: list[str]
    reasoning: str
    estimated_duration: int = Field(..., description="Minutes")
    supplies_needed: list[str]


class BatchInsightItem(BaseModel):
    patient_id: str
    status_summary: str
    next_action: str
    priority: str  # high, medium, low


class BatchInsightsRequest(BaseModel):
    patient_ids: list[str] = Field(..., min_length=1, max_length=50)


class BatchInsightsResponse(BaseModel):
    insights: list[BatchInsightItem]


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _call_darius(task: str) -> str:
    """Call Darius for LLM-powered text generation."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DARIUS_URL}/task",
                json={"task": task, "project": "orthoflow-ai"},
                timeout=45.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("args", {}).get("proposal", "")
    except httpx.TimeoutException:
        logger.error("darius_timeout", extra={"task_length": len(task)})
        raise HTTPException(503, "AI intelligence service timed out — try again")
    except httpx.HTTPStatusError as e:
        logger.error("darius_http_error", extra={"status": e.response.status_code})
        raise HTTPException(503, "AI intelligence service unavailable")
    except Exception as e:
        logger.error("darius_error", extra={"error": str(e)[:200]})
        raise HTTPException(503, f"AI intelligence service error: {str(e)[:100]}")


async def _get_patient_or_404(
    db: AsyncSession, patient_id: str, practice_id: str
) -> Patient:
    """Fetch patient scoped to practice, raise 404 if not found."""
    patient = (
        await db.execute(
            select(Patient).where(
                Patient.id == patient_id, Patient.practice_id == practice_id
            )
        )
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")
    return patient


async def _get_recent_notes(
    db: AsyncSession, patient_id: str, limit: int = 20
) -> list[TreatmentNote]:
    """Fetch recent treatment notes for a patient."""
    result = await db.execute(
        select(TreatmentNote)
        .where(TreatmentNote.patient_id == patient_id)
        .order_by(TreatmentNote.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def _get_tooth_chart_summary(db: AsyncSession, patient_id: str) -> str:
    """Build a concise tooth chart summary for LLM context."""
    chart = (
        await db.execute(
            select(ToothChart).where(ToothChart.patient_id == patient_id)
        )
    ).scalar_one_or_none()

    if not chart:
        return "No tooth chart on file."

    parts = []
    if chart.upper_wire:
        parts.append(f"Upper wire: {chart.upper_wire}")
    if chart.lower_wire:
        parts.append(f"Lower wire: {chart.lower_wire}")
    if chart.appliances:
        appliance_names = [a.get("type", "unknown") for a in chart.appliances if isinstance(a, dict)]
        if appliance_names:
            parts.append(f"Appliances: {', '.join(appliance_names)}")
    if chart.teeth_data:
        bracket_count = sum(1 for t in chart.teeth_data.values() if isinstance(t, dict) and t.get("bracket"))
        parts.append(f"Brackets placed: {bracket_count}/28")

    return "; ".join(parts) if parts else "Chart exists but no details recorded."


async def _get_recent_appointments(
    db: AsyncSession, patient_id: str, limit: int = 10
) -> list[Appointment]:
    """Fetch recent appointments for a patient."""
    result = await db.execute(
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.appointment_date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/summarize/{patient_id}", response_model=SummarizeResponse)
async def summarize_treatment(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Summarize a patient's treatment history from their last 20 notes.

    Returns a structured treatment summary, key milestones, and current status.
    """
    practice_id = user["practice_id"]
    patient = await _get_patient_or_404(db, patient_id, practice_id)
    notes = await _get_recent_notes(db, patient_id, limit=20)

    if not notes:
        raise HTTPException(400, "No treatment notes available to summarize")

    notes_text = "\n".join(
        f"[{n.created_at.strftime('%Y-%m-%d')}] {n.note_text[:300]}" for n in notes
    )

    prompt = f"""You are a clinical intelligence assistant for an orthodontic practice.
Summarize this patient's treatment history from their clinical notes.

PATIENT: {patient.first_name} {patient.last_name}
TREATMENT PHASE: {patient.treatment_phase or 'unknown'}
NOTES (most recent first, up to 20):
{notes_text}

RESPOND IN THIS EXACT FORMAT (no markdown, no extra text):
TREATMENT_SUMMARY: [A 2-4 sentence summary of the full treatment journey so far]
KEY_MILESTONES: [Comma-separated list of significant treatment events with approximate dates, e.g. "Bonded upper 2024-03, Wire progression to 18SS 2024-06, Elastics started 2024-09"]
CURRENT_STATUS: [One sentence describing where the patient is right now in their treatment]"""

    result = await _call_darius(prompt)

    # Parse response
    treatment_summary = ""
    key_milestones: list[str] = []
    current_status = ""

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("TREATMENT_SUMMARY:"):
            treatment_summary = line[len("TREATMENT_SUMMARY:"):].strip()
        elif line.startswith("KEY_MILESTONES:"):
            raw = line[len("KEY_MILESTONES:"):].strip()
            key_milestones = [m.strip() for m in raw.split(",") if m.strip()]
        elif line.startswith("CURRENT_STATUS:"):
            current_status = line[len("CURRENT_STATUS:"):].strip()

    # Fallback if parsing failed
    if not treatment_summary:
        treatment_summary = result.strip()[:500]
    if not current_status:
        current_status = f"Patient is in {patient.treatment_phase or 'unknown'} phase."

    await audit_log(
        db, practice_id, user["user_id"], "ai.summarize_treatment", "patient", patient_id
    )

    return SummarizeResponse(
        treatment_summary=treatment_summary,
        key_milestones=key_milestones,
        current_status=current_status,
    )


@router.post("/next-visit/{patient_id}", response_model=NextVisitResponse)
async def next_visit_suggestion(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Suggest what should happen at the patient's next visit.

    Uses treatment phase, recent notes, tooth chart, and appointment history
    to recommend procedures, estimate duration, and list supplies needed.
    """
    practice_id = user["practice_id"]
    patient = await _get_patient_or_404(db, patient_id, practice_id)
    notes = await _get_recent_notes(db, patient_id, limit=5)
    chart_summary = await _get_tooth_chart_summary(db, patient_id)
    appointments = await _get_recent_appointments(db, patient_id, limit=5)

    notes_text = "\n".join(
        f"[{n.created_at.strftime('%Y-%m-%d')}] {n.note_text[:200]}" for n in notes
    )
    appt_text = "\n".join(
        f"[{a.appointment_date.isoformat()}] {a.appointment_type or 'General'} ({a.status})"
        for a in appointments
    )

    prompt = f"""You are a clinical intelligence assistant for an orthodontic practice.
Based on the patient's treatment context, suggest what should happen at their next visit.

PATIENT: {patient.first_name} {patient.last_name}
TREATMENT PHASE: {patient.treatment_phase or 'unknown'}
TOOTH CHART: {chart_summary}

RECENT NOTES:
{notes_text or 'No recent notes.'}

RECENT APPOINTMENTS:
{appt_text or 'No recent appointments.'}

RESPOND IN THIS EXACT FORMAT (no markdown, no extra text):
SUGGESTED_PROCEDURES: [Comma-separated list of procedures to perform, e.g. "Wire change to 18x25 SS upper, Adjust lower NiTi, Check elastic wear"]
REASONING: [2-3 sentences explaining why these procedures are appropriate given the current treatment state]
ESTIMATED_DURATION: [Integer minutes, e.g. 30]
SUPPLIES_NEEDED: [Comma-separated list of supplies/materials to have ready, e.g. "18x25 SS upper archwire, Elastic hooks, Power chain"]"""

    result = await _call_darius(prompt)

    # Parse response
    suggested_procedures: list[str] = []
    reasoning = ""
    estimated_duration = 30
    supplies_needed: list[str] = []

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("SUGGESTED_PROCEDURES:"):
            raw = line[len("SUGGESTED_PROCEDURES:"):].strip()
            suggested_procedures = [p.strip() for p in raw.split(",") if p.strip()]
        elif line.startswith("REASONING:"):
            reasoning = line[len("REASONING:"):].strip()
        elif line.startswith("ESTIMATED_DURATION:"):
            raw = line[len("ESTIMATED_DURATION:"):].strip()
            try:
                estimated_duration = int("".join(c for c in raw if c.isdigit()) or "30")
            except ValueError:
                estimated_duration = 30
        elif line.startswith("SUPPLIES_NEEDED:"):
            raw = line[len("SUPPLIES_NEEDED:"):].strip()
            supplies_needed = [s.strip() for s in raw.split(",") if s.strip()]

    # Fallback
    if not suggested_procedures:
        suggested_procedures = ["Standard adjustment"]
    if not reasoning:
        reasoning = "Based on current treatment phase and recent progress."

    await audit_log(
        db, practice_id, user["user_id"], "ai.next_visit_suggestion", "patient", patient_id
    )

    return NextVisitResponse(
        suggested_procedures=suggested_procedures,
        reasoning=reasoning,
        estimated_duration=estimated_duration,
        supplies_needed=supplies_needed,
    )


@router.post("/batch-insights", response_model=BatchInsightsResponse)
async def batch_insights(
    body: BatchInsightsRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Generate quick AI insights for a batch of patients (morning huddle prep).

    Returns a status summary, next action, and priority for each patient.
    """
    practice_id = user["practice_id"]

    # Gather context for all patients
    patient_contexts: list[str] = []
    valid_ids: list[str] = []

    for pid in body.patient_ids:
        patient = (
            await db.execute(
                select(Patient).where(
                    Patient.id == pid, Patient.practice_id == practice_id
                )
            )
        ).scalar_one_or_none()
        if not patient:
            continue

        valid_ids.append(pid)

        # Get last note
        last_note = (
            await db.execute(
                select(TreatmentNote)
                .where(TreatmentNote.patient_id == pid)
                .order_by(TreatmentNote.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        note_text = last_note.note_text[:150] if last_note else "No notes"
        patient_contexts.append(
            f"ID:{pid} | {patient.first_name} {patient.last_name} | Phase: {patient.treatment_phase or 'unknown'} | Last note: {note_text}"
        )

    if not patient_contexts:
        raise HTTPException(400, "No valid patients found for the provided IDs")

    patients_block = "\n".join(patient_contexts)

    prompt = f"""You are a clinical intelligence assistant for an orthodontic practice.
Generate a quick insight for each patient for the morning huddle. Be concise — one line each.

PATIENTS:
{patients_block}

RESPOND IN THIS EXACT FORMAT (one line per patient, no markdown):
For each patient, output exactly:
INSIGHT: [patient_id] | [status_summary max 50 chars] | [next_action max 50 chars] | [priority: high/medium/low]

Output one INSIGHT line per patient listed above."""

    result = await _call_darius(prompt)

    # Parse response
    insights: list[BatchInsightItem] = []
    parsed_ids: set[str] = set()

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("INSIGHT:"):
            parts = line[len("INSIGHT:"):].strip().split("|")
            if len(parts) >= 4:
                pid = parts[0].strip()
                # Match against valid IDs (handle UUID prefix matching)
                matched_id = None
                for vid in valid_ids:
                    if vid == pid or vid.startswith(pid) or pid.startswith(vid[:8]):
                        matched_id = vid
                        break
                if matched_id and matched_id not in parsed_ids:
                    parsed_ids.add(matched_id)
                    priority = parts[3].strip().lower()
                    if priority not in ("high", "medium", "low"):
                        priority = "medium"
                    insights.append(
                        BatchInsightItem(
                            patient_id=matched_id,
                            status_summary=parts[1].strip()[:100],
                            next_action=parts[2].strip()[:100],
                            priority=priority,
                        )
                    )

    # Fill in any patients that weren't parsed with defaults
    for vid in valid_ids:
        if vid not in parsed_ids:
            insights.append(
                BatchInsightItem(
                    patient_id=vid,
                    status_summary="Unable to generate insight",
                    next_action="Review chart manually",
                    priority="medium",
                )
            )

    await audit_log(
        db, practice_id, user["user_id"], "ai.batch_insights", "patient",
        details=f"Batch of {len(valid_ids)} patients",
    )

    return BatchInsightsResponse(insights=insights)
