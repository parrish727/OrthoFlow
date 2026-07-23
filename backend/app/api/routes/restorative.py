"""OrthoFlow API — Restorative Tooth Charting (Sprint B).
Per-tooth conditions, surface-level restorations, treatment planning.
Additive — does not touch the ortho ToothChart.
"""
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.restorative import RestorativeChart, ToothRestoration

router = APIRouter(prefix="/api/v1/restorative", tags=["restorative-charting"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ToothConditionUpdate(BaseModel):
    tooth_number: int = Field(..., ge=1, le=32)
    condition: str  # healthy, caries, fractured, missing, impacted, etc.
    mobility: int | None = Field(None, ge=0, le=3)
    notes: str | None = None


class RestorationCreate(BaseModel):
    tooth_number: int = Field(..., ge=1, le=32)
    surfaces: str | None = None  # M, O, D, B, L, I combination
    cdt_code: str | None = None
    restoration_type: str  # filling, crown, veneer, implant, RCT, extraction, sealant
    material: str | None = None  # composite, amalgam, porcelain, gold, zirconia
    status: str = "existing"  # existing, planned, in_progress, completed, referred
    date_placed: date | None = None
    date_planned: date | None = None
    notes: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/patients/{patient_id}/chart")
async def get_restorative_chart(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the full restorative chart for a patient (conditions + all restorations)."""
    result = await db.execute(
        select(RestorativeChart).where(
            RestorativeChart.patient_id == uuid.UUID(patient_id),
            RestorativeChart.practice_id == uuid.UUID(user["practice_id"]),
        )
    )
    chart = result.scalar_one_or_none()

    if not chart:
        return {"teeth_conditions": {}, "restorations": [], "exists": False}

    # Get all restorations
    rest_result = await db.execute(
        select(ToothRestoration)
        .where(ToothRestoration.chart_id == chart.id)
        .order_by(ToothRestoration.tooth_number, ToothRestoration.created_at.desc())
    )
    restorations = rest_result.scalars().all()

    return {
        "exists": True,
        "teeth_conditions": chart.teeth_conditions or {},
        "restorations": [
            {
                "id": str(r.id),
                "tooth_number": r.tooth_number,
                "surfaces": r.surfaces,
                "cdt_code": r.cdt_code,
                "restoration_type": r.restoration_type,
                "material": r.material,
                "status": r.status,
                "date_placed": r.date_placed.isoformat() if r.date_placed else None,
                "date_planned": r.date_planned.isoformat() if r.date_planned else None,
                "notes": r.notes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in restorations
        ],
        "updated_at": chart.updated_at.isoformat() if chart.updated_at else None,
    }


@router.put("/patients/{patient_id}/chart/tooth")
async def update_tooth_condition(
    patient_id: str,
    payload: ToothConditionUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update condition for a specific tooth (create chart if needed)."""
    practice_id = uuid.UUID(user["practice_id"])
    pat_id = uuid.UUID(patient_id)

    # Get or create chart
    result = await db.execute(
        select(RestorativeChart).where(
            RestorativeChart.patient_id == pat_id,
            RestorativeChart.practice_id == practice_id,
        )
    )
    chart = result.scalar_one_or_none()

    if not chart:
        chart = RestorativeChart(
            practice_id=practice_id,
            patient_id=pat_id,
            teeth_conditions={},
        )
        db.add(chart)
        await db.flush()

    # Update the specific tooth
    conditions = chart.teeth_conditions or {}
    conditions[str(payload.tooth_number)] = {
        "condition": payload.condition,
        "mobility": payload.mobility,
        "notes": payload.notes,
    }
    chart.teeth_conditions = conditions
    chart.updated_by = uuid.UUID(user["user_id"])

    # Force SQLAlchemy to detect JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(chart, "teeth_conditions")

    await db.commit()
    return {"status": "updated", "tooth": str(payload.tooth_number)}


@router.post("/patients/{patient_id}/restorations", status_code=status.HTTP_201_CREATED)
async def add_restoration(
    patient_id: str,
    payload: RestorationCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Add a restoration record to a patient's chart."""
    practice_id = uuid.UUID(user["practice_id"])
    pat_id = uuid.UUID(patient_id)

    # Get or create chart
    result = await db.execute(
        select(RestorativeChart).where(
            RestorativeChart.patient_id == pat_id,
            RestorativeChart.practice_id == practice_id,
        )
    )
    chart = result.scalar_one_or_none()

    if not chart:
        chart = RestorativeChart(
            practice_id=practice_id,
            patient_id=pat_id,
            teeth_conditions={},
        )
        db.add(chart)
        await db.flush()

    # Create the restoration record
    restoration = ToothRestoration(
        chart_id=chart.id,
        practice_id=practice_id,
        patient_id=pat_id,
        tooth_number=payload.tooth_number,
        surfaces=payload.surfaces,
        cdt_code=payload.cdt_code,
        restoration_type=payload.restoration_type,
        material=payload.material,
        status=payload.status,
        provider_id=uuid.UUID(user["user_id"]),
        date_placed=payload.date_placed,
        date_planned=payload.date_planned,
        notes=payload.notes,
    )
    db.add(restoration)
    await db.commit()

    return {"id": str(restoration.id), "status": "created"}


@router.get("/patients/{patient_id}/restorations/tooth/{tooth_number}")
async def get_tooth_history(
    patient_id: str,
    tooth_number: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get full restoration history for a specific tooth."""
    result = await db.execute(
        select(ToothRestoration).where(
            ToothRestoration.patient_id == uuid.UUID(patient_id),
            ToothRestoration.practice_id == uuid.UUID(user["practice_id"]),
            ToothRestoration.tooth_number == tooth_number,
        ).order_by(ToothRestoration.created_at.desc())
    )
    restorations = result.scalars().all()

    return {
        "tooth_number": tooth_number,
        "restorations": [
            {
                "id": str(r.id),
                "surfaces": r.surfaces,
                "cdt_code": r.cdt_code,
                "restoration_type": r.restoration_type,
                "material": r.material,
                "status": r.status,
                "date_placed": r.date_placed.isoformat() if r.date_placed else None,
                "notes": r.notes,
            }
            for r in restorations
        ],
        "total": len(restorations),
    }


@router.get("/patients/{patient_id}/treatment-plan")
async def get_treatment_plan(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get all planned/in-progress restorations for a patient (treatment plan view)."""
    result = await db.execute(
        select(ToothRestoration).where(
            ToothRestoration.patient_id == uuid.UUID(patient_id),
            ToothRestoration.practice_id == uuid.UUID(user["practice_id"]),
            ToothRestoration.status.in_(["planned", "in_progress"]),
        ).order_by(ToothRestoration.tooth_number)
    )
    planned = result.scalars().all()

    return {
        "planned_procedures": [
            {
                "id": str(r.id),
                "tooth_number": r.tooth_number,
                "surfaces": r.surfaces,
                "cdt_code": r.cdt_code,
                "restoration_type": r.restoration_type,
                "material": r.material,
                "status": r.status,
                "date_planned": r.date_planned.isoformat() if r.date_planned else None,
                "notes": r.notes,
            }
            for r in planned
        ],
        "total": len(planned),
    }
