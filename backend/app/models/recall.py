"""
OrthoFlow AI — Hygiene Recall System (Sprint D)
Automated recall scheduling for prophy, perio maintenance, fluoride, and sealant checks.
Configurable intervals per patient with auto-scheduling and compliance tracking.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HygieneRecall(Base):
    """Hygiene recall scheduling record for a patient.

    Tracks recall type, interval, and automatically calculates next due date
    based on last visit date + interval_months.
    """
    __tablename__ = "hygiene_recalls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    recall_type: Mapped[str] = mapped_column(String(30), nullable=False)  # prophy, perio_maintenance, fluoride, sealant_check
    interval_months: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    last_visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active, overdue, completed, paused
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_schedule: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_recall_practice_status", "practice_id", "status"),
        Index("idx_recall_patient", "patient_id"),
        Index("idx_recall_practice_next_due", "practice_id", "next_due_date"),
    )
