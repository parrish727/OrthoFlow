"""OrthoFlow API — AI Treatment Timeline Predictions.

Routes timeline prediction requests through Darius for:
- Estimated months remaining in treatment
- Milestone predictions with approximate dates
- Delay factor identification
Also provides SQL-aggregated practice benchmarks (no AI).
"""
import logging
import os
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.clinical import Patient, Appointment, TreatmentNote, ToothChart

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai/timeline", tags=["ai-timeline"])

DARIUS_URL = os.environ.get("DARIUS_URL", "http://darius-agent:8000")


# ── Schemas ───────────────────────────────────────────────────────────────────


class Milestone(BaseModel):
    description: str
    estimated_date: str  # YYYY-MM or relative ("in ~3 months")
    confidence: str  # high, medium, low


class TimelinePredictionResponse(BaseModel):
    estimated_months_remaining: int
    next_milestones: list[Milestone]
    confidence_level: str  # high, medium, low
    factors_that_could_delay: list[str]


class PhaseBenchmark(BaseModel):
    treatment_phase: str
    avg_months: float
    patient_count: int
    min_months: float
    max_months: float


class BenchmarksResponse(BaseModel):
    benchmarks: list[PhaseBenchmark]
    total_patients_analyzed: int


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
        logger.error("darius_timeout_timeline")
        raise HTTPException(503, "AI timeline service timed out — try again")
    except httpx.HTTPStatusError as e:
        logger.error("darius_http_error", extra={"status": e.response.status_code})
        raise HTTPException(503, "AI timeline service unavailable")
    except Exception as e:
        logger.error("darius_error", extra={"error": str(e)[:200]})
        raise HTTPException(503, f"AI timeline service error: {str(e)[:100]}")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/predict/{patient_id}", response_model=TimelinePredictionResponse)
async def predict_timeline(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Predict treatment timeline for a patient.

    Uses treatment phase, time in treatment, procedures completed, and
    tooth chart state to estimate remaining duration and upcoming milestones.
    """
    practice_id = user["practice_id"]

    # Get patient
    patient = (
        await db.execute(
            select(Patient).where(
                Patient.id == patient_id, Patient.practice_id == practice_id
            )
        )
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Calculate time in treatment
    first_appointment = (
        await db.execute(
            select(Appointment)
            .where(
                Appointment.patient_id == patient_id,
                Appointment.status == "completed",
            )
            .order_by(Appointment.appointment_date.asc())
            .limit(1)
        )
    ).scalar_one_or_none()

    months_in_treatment = 0
    if first_appointment:
        delta = date.today() - first_appointment.appointment_date
        months_in_treatment = max(1, delta.days // 30)

    # Count completed appointments
    completed_count = (
        await db.execute(
            select(func.count(Appointment.id)).where(
                Appointment.patient_id == patient_id,
                Appointment.status == "completed",
            )
        )
    ).scalar() or 0

    # Recent notes for context
    notes = (
        await db.execute(
            select(TreatmentNote)
            .where(TreatmentNote.patient_id == patient_id)
            .order_by(TreatmentNote.created_at.desc())
            .limit(5)
        )
    ).scalars().all()

    notes_text = "\n".join(
        f"  [{n.created_at.strftime('%Y-%m-%d')}] {n.note_text[:150]}" for n in notes
    )

    # Tooth chart state
    chart = (
        await db.execute(
            select(ToothChart).where(ToothChart.patient_id == patient_id)
        )
    ).scalar_one_or_none()

    chart_summary = "No chart data"
    if chart:
        parts = []
        if chart.upper_wire:
            parts.append(f"Upper wire: {chart.upper_wire}")
            if chart.upper_wire_date:
                parts.append(f"(placed {chart.upper_wire_date.isoformat()})")
        if chart.lower_wire:
            parts.append(f"Lower wire: {chart.lower_wire}")
            if chart.lower_wire_date:
                parts.append(f"(placed {chart.lower_wire_date.isoformat()})")
        if chart.appliances:
            appliance_info = [
                f"{a.get('type', 'unknown')}" for a in chart.appliances if isinstance(a, dict)
            ]
            if appliance_info:
                parts.append(f"Appliances: {', '.join(appliance_info)}")
        if chart.teeth_data:
            bracket_count = sum(
                1 for t in chart.teeth_data.values()
                if isinstance(t, dict) and t.get("bracket")
            )
            parts.append(f"Brackets: {bracket_count}/28")
        chart_summary = "; ".join(parts) if parts else "Chart exists but minimal data"

    # Get procedure types from appointments
    recent_procedures = (
        await db.execute(
            select(Appointment.appointment_type)
            .where(
                Appointment.patient_id == patient_id,
                Appointment.status == "completed",
                Appointment.appointment_type.isnot(None),
            )
            .order_by(Appointment.appointment_date.desc())
            .limit(10)
        )
    ).scalars().all()

    procedures_text = ", ".join(set(recent_procedures)) if recent_procedures else "No procedure types recorded"

    prompt = f"""You are a clinical timeline predictor for an orthodontic practice.
Predict the remaining treatment timeline for this patient based on their current state.

PATIENT: {patient.first_name} {patient.last_name}
TREATMENT PHASE: {patient.treatment_phase or 'unknown'}
MONTHS IN TREATMENT: {months_in_treatment}
COMPLETED APPOINTMENTS: {completed_count}
PROCEDURES PERFORMED: {procedures_text}

TOOTH CHART STATE:
{chart_summary}

RECENT CLINICAL NOTES:
{notes_text or 'No recent notes'}

Consider typical orthodontic treatment durations:
- Full comprehensive: 18-30 months
- Phase I (early): 6-12 months
- Phase II: 12-24 months
- Limited treatment: 6-12 months
- Finishing/detailing after major mechanics: 3-6 months
- Retention transition after active: 1-2 months

RESPOND IN THIS EXACT FORMAT (no markdown):
ESTIMATED_MONTHS_REMAINING: [Integer, e.g. 12]
CONFIDENCE_LEVEL: [high, medium, or low]
MILESTONES: [Pipe-separated list of upcoming milestones with timing, format: "description~timing~confidence" e.g. "Wire progression to 19x25 SS~in 2 months~high|Begin finishing elastics~in 4 months~medium|Debond and retention~in 8 months~medium"]
DELAY_FACTORS: [Comma-separated list of things that could extend treatment, e.g. "Poor elastic wear compliance, Missed appointments, Impacted teeth requiring surgical exposure, Root resorption requiring rest periods"]"""

    result = await _call_darius(prompt)

    # Parse response
    estimated_months = 12
    confidence_level = "medium"
    milestones: list[Milestone] = []
    delay_factors: list[str] = []

    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("ESTIMATED_MONTHS_REMAINING:"):
            raw = line[len("ESTIMATED_MONTHS_REMAINING:"):].strip()
            try:
                estimated_months = max(1, int("".join(c for c in raw if c.isdigit()) or "12"))
            except ValueError:
                estimated_months = 12
        elif line.startswith("CONFIDENCE_LEVEL:"):
            raw = line[len("CONFIDENCE_LEVEL:"):].strip().lower()
            if raw in ("high", "medium", "low"):
                confidence_level = raw
        elif line.startswith("MILESTONES:"):
            raw = line[len("MILESTONES:"):].strip()
            for milestone_str in raw.split("|"):
                parts = milestone_str.strip().split("~")
                if len(parts) >= 2:
                    conf = parts[2].strip().lower() if len(parts) >= 3 else "medium"
                    if conf not in ("high", "medium", "low"):
                        conf = "medium"
                    milestones.append(
                        Milestone(
                            description=parts[0].strip(),
                            estimated_date=parts[1].strip(),
                            confidence=conf,
                        )
                    )
        elif line.startswith("DELAY_FACTORS:"):
            raw = line[len("DELAY_FACTORS:"):].strip()
            delay_factors = [f.strip() for f in raw.split(",") if f.strip()]

    # Fallbacks
    if not milestones:
        milestones = [
            Milestone(
                description="Continue current treatment phase",
                estimated_date=f"in ~{estimated_months // 2} months",
                confidence="low",
            )
        ]
    if not delay_factors:
        delay_factors = ["Patient compliance", "Biological response variability"]

    await audit_log(
        db, practice_id, user["user_id"], "ai.timeline_prediction", "patient",
        patient_id,
        details=f"Predicted {estimated_months} months remaining ({confidence_level} confidence)",
    )

    return TimelinePredictionResponse(
        estimated_months_remaining=estimated_months,
        next_milestones=milestones,
        confidence_level=confidence_level,
        factors_that_could_delay=delay_factors,
    )


@router.get("/benchmarks", response_model=BenchmarksResponse)
async def treatment_benchmarks(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return average treatment timelines by phase for the practice.

    Pure SQL aggregation — no AI. Computes from historical appointment
    and patient data to establish practice-specific baselines.
    """
    practice_id = user["practice_id"]

    # Get patients who have completed treatment (or have enough history)
    # For each treatment phase, compute time spent by looking at appointment spans
    # Strategy: for patients who transitioned phases, measure time in each phase
    # Simpler approach: measure time from first to last appointment per patient,
    # grouped by their current phase (gives avg total treatment time per phase cohort)

    # Get all patients with at least 2 completed appointments
    patient_stats_query = (
        select(
            Patient.treatment_phase,
            Patient.id.label("patient_id"),
            func.min(Appointment.appointment_date).label("first_appt"),
            func.max(Appointment.appointment_date).label("last_appt"),
            func.count(Appointment.id).label("appt_count"),
        )
        .join(Appointment, Appointment.patient_id == Patient.id)
        .where(
            Patient.practice_id == practice_id,
            Appointment.status == "completed",
        )
        .group_by(Patient.treatment_phase, Patient.id)
        .having(func.count(Appointment.id) >= 2)
    )

    result = await db.execute(patient_stats_query)
    rows = result.all()

    if not rows:
        await audit_log(
            db, practice_id, user["user_id"], "ai.timeline_benchmarks", "practice",
            details="No sufficient data for benchmarks",
        )
        return BenchmarksResponse(benchmarks=[], total_patients_analyzed=0)

    # Aggregate by phase
    phase_data: dict[str, list[float]] = {}
    for row in rows:
        phase = row.treatment_phase or "unknown"
        if row.first_appt and row.last_appt:
            days = (row.last_appt - row.first_appt).days
            months = max(0.5, days / 30.0)  # minimum 0.5 months
            phase_data.setdefault(phase, []).append(months)

    benchmarks: list[PhaseBenchmark] = []
    total_patients = 0

    for phase, month_values in sorted(phase_data.items()):
        if not month_values:
            continue
        total_patients += len(month_values)
        benchmarks.append(
            PhaseBenchmark(
                treatment_phase=phase,
                avg_months=round(sum(month_values) / len(month_values), 1),
                patient_count=len(month_values),
                min_months=round(min(month_values), 1),
                max_months=round(max(month_values), 1),
            )
        )

    # Sort by patient count descending
    benchmarks.sort(key=lambda b: b.patient_count, reverse=True)

    await audit_log(
        db, practice_id, user["user_id"], "ai.timeline_benchmarks", "practice",
        details=f"Generated benchmarks from {total_patients} patients across {len(benchmarks)} phases",
    )

    return BenchmarksResponse(
        benchmarks=benchmarks,
        total_patients_analyzed=total_patients,
    )
