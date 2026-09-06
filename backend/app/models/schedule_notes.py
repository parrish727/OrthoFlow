"""OrthoFlow — Schedule Notes (AI + DA daily notes synced to the day's schedule).

Precognitive intent (see .kiro/steering/product-context.md): the schedule shouldn't just
show appointments — it should surface the day's human context the team is already tracking.
DA personal notes ("Priscilla Best leaving early today"), manager notes ("Consultant visiting
the DA team today re: last month's findings"), and AI-surfaced observations all appear inline
with the schedule so the whole team shares the same situational awareness.

A ScheduleNote is tied to a practice + a specific date. `origin` distinguishes AI-surfaced
notes from human ones; `source_da_id` links a note to a DA so it stays in sync with that DA's
personal notes. `placement` controls whether it renders above or below the schedule grid.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import String, Text, Boolean, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScheduleNote(Base):
    __tablename__ = "schedule_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("practices.id"), nullable=False)
    note_date: Mapped[date] = mapped_column(Date, nullable=False)

    # origin: 'ai' (system-surfaced), 'da' (dental-assistant personal note synced up),
    #         'manager', 'front_desk', 'doctor'
    origin: Mapped[str] = mapped_column(String(20), nullable=False, default="da")
    # category: 'staffing' | 'patient' | 'operational' | 'clinical' | 'insight'
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="operational")
    # placement: 'above' | 'below' the schedule grid
    placement: Mapped[str] = mapped_column(String(10), nullable=False, default="above")
    # severity/tone for UI accent: 'info' | 'highlight' | 'warning'
    tone: Mapped[str] = mapped_column(String(10), nullable=False, default="info")

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional linkage so notes stay in sync with a DA's personal notes / a patient.
    source_da_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dental_assistants.id"))
    patient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"))

    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_schedule_notes_practice_date", "practice_id", "note_date"),
        Index("idx_schedule_notes_da", "source_da_id"),
    )
