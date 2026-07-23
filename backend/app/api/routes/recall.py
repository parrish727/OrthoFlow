"""OrthoFlow API — Hygiene Recall System (Sprint D).
Automated recall scheduling with configurable intervals and compliance tracking.
"""
import uuid
from datetime import date
from dateutil.relativedelta import relativedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.recall import HygieneRecall

router = APIRouter(prefix="/api/v1/recall", tags=["hygiene-recall"])

VALID_RECALL_TYPES = {"prophy", "perio_maintenance", "fluoride", "sealant_check"}
VALID_STATUSES = {"active", "overdue", "completed", "paused"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class RecallCreate(BaseModel):
    recall_type: str = Field(..., pattern=r"^(prophy|perio_maintenance|fluoride|sealant_check)$")
    interval_months: int = Field(6, ge=1, le=24)
    auto_schedule: bool = True
    notes: str | None = None


class RecallResponse(BaseModel):
    id: str
    patient_id: str
    recall_type: str
    interval_months: int
    last_visit_date: date | None
    next_due_date: date | None
    status: str
    notes: str | None
    auto_schedule: bool

    class Config:
        from_attributes = True


class RecallStatsResponse(BaseModel):
    total_active: int
    due_this_month: int
    overdue_count: int
    compliance_rate: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_recall(recall: HygieneRecall) -> dict:
    return {
        "id": str(recall.id),
        "patient_id": str(recall.patient_id),
        "recall_type": recall.recall_type,
        "interval_months": recall.interval_months,
        "last_visit_date": recall.last_visit_date.isoformat() if recall.last_visit_date else None,
        "next_due_date": recall.next_due_date.isoformat() if recall.next_due_date else None,
        "status": recall.status,
        "notes": recall.notes,
        "auto_schedule": recall.auto_schedule,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/patients/{patient_id}")
async def get_patient_recalls(
    patient_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all recall settings for a patient (practice-scoped)."""
    practice_id = user["practice_id"]
    result = await db.execute(
        select(HygieneRecall).where(
            and_(
                HygieneRecall.practice_id == practice_id,
                HygieneRecall.patient_id == patient_id,
            )
        )
    )
    recalls = result.scalars().all()
    return [_serialize_recall(r) for r in recalls]


@router.post("/patients/{patient_id}", status_code=status.HTTP_201_CREATED)
async def create_or_update_recall(
    patient_id: uuid.UUID,
    payload: RecallCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create or update a recall for a patient (upsert by recall_type)."""
    practice_id = user["practice_id"]

    # Check if recall of this type already exists for patient
    result = await db.execute(
        select(HygieneRecall).where(
            and_(
                HygieneRecall.practice_id == practice_id,
                HygieneRecall.patient_id == patient_id,
                HygieneRecall.recall_type == payload.recall_type,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.interval_months = payload.interval_months
        existing.auto_schedule = payload.auto_schedule
        if payload.notes is not None:
            existing.notes = payload.notes
        # Recalculate next_due_date if last_visit_date exists
        if existing.last_visit_date:
            existing.next_due_date = existing.last_visit_date + relativedelta(months=payload.interval_months)
        await db.commit()
        await db.refresh(existing)
        return _serialize_recall(existing)

    recall = HygieneRecall(
        practice_id=practice_id,
        patient_id=patient_id,
        recall_type=payload.recall_type,
        interval_months=payload.interval_months,
        auto_schedule=payload.auto_schedule,
        notes=payload.notes,
        status="active",
    )
    db.add(recall)
    await db.commit()
    await db.refresh(recall)
    return _serialize_recall(recall)


@router.get("/due-list")
async def get_due_list(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all patients due or overdue for recall (practice-scoped), sorted by next_due_date."""
    practice_id = user["practice_id"]
    today = date.today()
    result = await db.execute(
        select(HygieneRecall).where(
            and_(
                HygieneRecall.practice_id == practice_id,
                HygieneRecall.status.in_(["active", "overdue"]),
                HygieneRecall.next_due_date.isnot(None),
                HygieneRecall.next_due_date <= today,
            )
        ).order_by(HygieneRecall.next_due_date.asc())
    )
    recalls = result.scalars().all()
    return [_serialize_recall(r) for r in recalls]


@router.post("/patients/{patient_id}/complete")
async def complete_recall(
    patient_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark recall as completed: updates last_visit_date, calculates next_due_date."""
    practice_id = user["practice_id"]
    today = date.today()

    result = await db.execute(
        select(HygieneRecall).where(
            and_(
                HygieneRecall.practice_id == practice_id,
                HygieneRecall.patient_id == patient_id,
                HygieneRecall.status.in_(["active", "overdue"]),
            )
        )
    )
    recalls = result.scalars().all()

    if not recalls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active recall found for patient {patient_id}",
        )

    completed = []
    for recall in recalls:
        recall.last_visit_date = today
        recall.next_due_date = today + relativedelta(months=recall.interval_months)
        recall.status = "active"  # Reset to active with new due date
        completed.append(recall)

    await db.commit()
    for r in completed:
        await db.refresh(r)
    return [_serialize_recall(r) for r in completed]


@router.get("/overdue")
async def get_overdue(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get patients overdue for recall (next_due_date < today)."""
    practice_id = user["practice_id"]
    today = date.today()
    result = await db.execute(
        select(HygieneRecall).where(
            and_(
                HygieneRecall.practice_id == practice_id,
                HygieneRecall.status.in_(["active", "overdue"]),
                HygieneRecall.next_due_date.isnot(None),
                HygieneRecall.next_due_date < today,
            )
        ).order_by(HygieneRecall.next_due_date.asc())
    )
    recalls = result.scalars().all()
    return [_serialize_recall(r) for r in recalls]


@router.get("/stats")
async def get_recall_stats(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Recall stats: total active, due this month, overdue count, compliance rate."""
    practice_id = user["practice_id"]
    today = date.today()
    month_end = date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)

    # Total active recalls
    total_result = await db.execute(
        select(func.count(HygieneRecall.id)).where(
            and_(
                HygieneRecall.practice_id == practice_id,
                HygieneRecall.status.in_(["active", "overdue"]),
            )
        )
    )
    total_active = total_result.scalar() or 0

    # Due this month
    due_month_result = await db.execute(
        select(func.count(HygieneRecall.id)).where(
            and_(
                HygieneRecall.practice_id == practice_id,
                HygieneRecall.status.in_(["active", "overdue"]),
                HygieneRecall.next_due_date.isnot(None),
                HygieneRecall.next_due_date >= today,
                HygieneRecall.next_due_date < month_end,
            )
        )
    )
    due_this_month = due_month_result.scalar() or 0

    # Overdue count
    overdue_result = await db.execute(
        select(func.count(HygieneRecall.id)).where(
            and_(
                HygieneRecall.practice_id == practice_id,
                HygieneRecall.status.in_(["active", "overdue"]),
                HygieneRecall.next_due_date.isnot(None),
                HygieneRecall.next_due_date < today,
            )
        )
    )
    overdue_count = overdue_result.scalar() or 0

    # Compliance rate: completed / (completed + overdue)
    completed_result = await db.execute(
        select(func.count(HygieneRecall.id)).where(
            and_(
                HygieneRecall.practice_id == practice_id,
                HygieneRecall.status == "completed",
            )
        )
    )
    completed_count = completed_result.scalar() or 0
    total_for_rate = completed_count + overdue_count
    compliance_rate = round((completed_count / total_for_rate * 100), 1) if total_for_rate > 0 else 100.0

    return {
        "total_active": total_active,
        "due_this_month": due_this_month,
        "overdue_count": overdue_count,
        "compliance_rate": compliance_rate,
    }
