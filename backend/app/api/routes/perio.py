"""OrthoFlow API — Periodontal Charting (Sprint C).
Full 6-point probing: DB, B, MB, DL, L, ML per tooth.
192 data points per complete exam (32 teeth × 6 sites).
"""
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.perio import PerioExam, PerioReading

router = APIRouter(prefix="/api/v1/perio", tags=["perio-charting"])

VALID_SITES = {"DB", "B", "MB", "DL", "L", "ML"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class PerioExamCreate(BaseModel):
    exam_date: date
    notes: str | None = None


class PerioReadingCreate(BaseModel):
    tooth_number: int = Field(..., ge=1, le=32)
    site: str = Field(..., pattern=r"^(DB|B|MB|DL|L|ML)$")
    probing_depth: int = Field(..., ge=0, le=20)
    recession: int = Field(0, ge=0, le=20)
    bleeding_on_probing: bool = False
    suppuration: bool = False
    furcation_grade: int | None = Field(None, ge=0, le=3)
    mobility_grade: int | None = Field(None, ge=0, le=3)
    plaque: bool = False


class PerioReadingsBatch(BaseModel):
    readings: list[PerioReadingCreate]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/patients/{patient_id}/exams")
async def list_perio_exams(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all periodontal exams for a patient (practice-scoped)."""
    result = await db.execute(
        select(PerioExam)
        .where(
            PerioExam.patient_id == uuid.UUID(patient_id),
            PerioExam.practice_id == uuid.UUID(user["practice_id"]),
        )
        .order_by(PerioExam.exam_date.desc())
    )
    exams = result.scalars().all()

    return {
        "exams": [
            {
                "id": str(e.id),
                "exam_date": e.exam_date.isoformat(),
                "examiner_id": str(e.examiner_id),
                "notes": e.notes,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in exams
        ],
        "total": len(exams),
    }


@router.post("/patients/{patient_id}/exams", status_code=status.HTTP_201_CREATED)
async def create_perio_exam(
    patient_id: str,
    payload: PerioExamCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Create a new periodontal exam record."""
    exam = PerioExam(
        practice_id=uuid.UUID(user["practice_id"]),
        patient_id=uuid.UUID(patient_id),
        exam_date=payload.exam_date,
        examiner_id=uuid.UUID(user["user_id"]),
        notes=payload.notes,
    )
    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    return {"id": str(exam.id), "status": "created"}


@router.get("/exams/{exam_id}")
async def get_perio_exam(
    exam_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a full perio exam with all readings."""
    result = await db.execute(
        select(PerioExam)
        .options(selectinload(PerioExam.readings))
        .where(
            PerioExam.id == uuid.UUID(exam_id),
            PerioExam.practice_id == uuid.UUID(user["practice_id"]),
        )
    )
    exam = result.scalar_one_or_none()

    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perio exam not found")

    return {
        "id": str(exam.id),
        "patient_id": str(exam.patient_id),
        "exam_date": exam.exam_date.isoformat(),
        "examiner_id": str(exam.examiner_id),
        "notes": exam.notes,
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
        "readings": [
            {
                "id": str(r.id),
                "tooth_number": r.tooth_number,
                "site": r.site,
                "probing_depth": r.probing_depth,
                "recession": r.recession,
                "clinical_attachment_level": r.probing_depth + r.recession,
                "bleeding_on_probing": r.bleeding_on_probing,
                "suppuration": r.suppuration,
                "plaque": r.plaque,
                "furcation_grade": r.furcation_grade,
                "mobility_grade": r.mobility_grade,
            }
            for r in exam.readings
        ],
        "total_readings": len(exam.readings),
    }


@router.post("/exams/{exam_id}/readings", status_code=status.HTTP_201_CREATED)
async def batch_save_readings(
    exam_id: str,
    payload: PerioReadingsBatch,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Batch-save perio readings for an exam (6 sites per tooth)."""
    # Verify exam exists and belongs to this practice
    result = await db.execute(
        select(PerioExam).where(
            PerioExam.id == uuid.UUID(exam_id),
            PerioExam.practice_id == uuid.UUID(user["practice_id"]),
        )
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perio exam not found")

    # Validate sites
    for reading in payload.readings:
        if reading.site not in VALID_SITES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid site '{reading.site}'. Must be one of: {', '.join(sorted(VALID_SITES))}",
            )

    # Create readings
    created = []
    for r in payload.readings:
        reading = PerioReading(
            exam_id=exam.id,
            tooth_number=r.tooth_number,
            site=r.site,
            probing_depth=r.probing_depth,
            recession=r.recession,
            bleeding_on_probing=r.bleeding_on_probing,
            suppuration=r.suppuration,
            furcation_grade=r.furcation_grade,
            mobility_grade=r.mobility_grade,
            plaque=r.plaque,
        )
        db.add(reading)
        created.append(reading)

    await db.commit()

    return {"saved": len(created), "exam_id": str(exam.id)}


@router.get("/patients/{patient_id}/summary")
async def get_perio_summary(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Periodontal summary: avg probing depth, % BOP, pockets >4mm, comparison to prior exam."""
    practice_id = uuid.UUID(user["practice_id"])
    pat_id = uuid.UUID(patient_id)

    # Get the most recent exam
    latest_result = await db.execute(
        select(PerioExam)
        .where(
            PerioExam.patient_id == pat_id,
            PerioExam.practice_id == practice_id,
        )
        .order_by(PerioExam.exam_date.desc())
        .limit(1)
    )
    latest_exam = latest_result.scalar_one_or_none()

    if not latest_exam:
        return {"has_data": False, "message": "No periodontal exams on record"}

    # Get readings for latest exam
    readings_result = await db.execute(
        select(PerioReading).where(PerioReading.exam_id == latest_exam.id)
    )
    readings = readings_result.scalars().all()

    if not readings:
        return {
            "has_data": True,
            "exam_id": str(latest_exam.id),
            "exam_date": latest_exam.exam_date.isoformat(),
            "message": "Exam exists but no readings recorded yet",
        }

    # Calculate summary stats
    total_sites = len(readings)
    avg_probing_depth = sum(r.probing_depth for r in readings) / total_sites
    bleeding_sites = sum(1 for r in readings if r.bleeding_on_probing)
    pct_bleeding = (bleeding_sites / total_sites) * 100
    deep_pockets = [r for r in readings if r.probing_depth > 4]
    teeth_with_deep_pockets = sorted(set(r.tooth_number for r in deep_pockets))

    summary = {
        "has_data": True,
        "exam_id": str(latest_exam.id),
        "exam_date": latest_exam.exam_date.isoformat(),
        "total_sites_recorded": total_sites,
        "avg_probing_depth_mm": round(avg_probing_depth, 1),
        "bleeding_on_probing_pct": round(pct_bleeding, 1),
        "sites_with_bop": bleeding_sites,
        "pockets_over_4mm": len(deep_pockets),
        "teeth_with_deep_pockets": teeth_with_deep_pockets,
        "suppuration_sites": sum(1 for r in readings if r.suppuration),
        "plaque_sites": sum(1 for r in readings if r.plaque),
    }

    # Compare to previous exam if one exists
    prev_result = await db.execute(
        select(PerioExam)
        .where(
            PerioExam.patient_id == pat_id,
            PerioExam.practice_id == practice_id,
            PerioExam.id != latest_exam.id,
        )
        .order_by(PerioExam.exam_date.desc())
        .limit(1)
    )
    prev_exam = prev_result.scalar_one_or_none()

    if prev_exam:
        prev_readings_result = await db.execute(
            select(PerioReading).where(PerioReading.exam_id == prev_exam.id)
        )
        prev_readings = prev_readings_result.scalars().all()

        if prev_readings:
            prev_total = len(prev_readings)
            prev_avg_depth = sum(r.probing_depth for r in prev_readings) / prev_total
            prev_bleeding = sum(1 for r in prev_readings if r.bleeding_on_probing)
            prev_pct_bleeding = (prev_bleeding / prev_total) * 100
            prev_deep = sum(1 for r in prev_readings if r.probing_depth > 4)

            summary["comparison"] = {
                "previous_exam_id": str(prev_exam.id),
                "previous_exam_date": prev_exam.exam_date.isoformat(),
                "depth_change_mm": round(avg_probing_depth - prev_avg_depth, 1),
                "bop_change_pct": round(pct_bleeding - prev_pct_bleeding, 1),
                "deep_pocket_change": len(deep_pockets) - prev_deep,
            }

    return summary
