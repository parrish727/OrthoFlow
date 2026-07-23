"""
OrthoFlow AI — Periodontal Charting (Sprint C)
Full 6-point probing per tooth: DB, B, MB, DL, L, ML.
192 data points per complete exam (32 teeth × 6 sites).
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PerioExam(Base):
    """A single periodontal examination record for a patient.

    Each exam contains up to 192 PerioReading rows (32 teeth × 6 sites).
    Tracks examiner, date, and freeform notes.
    """
    __tablename__ = "perio_exams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    examiner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    readings: Mapped[list["PerioReading"]] = relationship(back_populates="exam", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_perio_exam_patient", "patient_id"),
        Index("idx_perio_exam_practice_date", "practice_id", "exam_date"),
    )


class PerioReading(Base):
    """Individual site measurement within a perio exam.

    Sites use standard 6-point notation:
      DB (distobuccal), B (buccal), MB (mesiobuccal),
      DL (distolingual), L (lingual), ML (mesiolingual)
    """
    __tablename__ = "perio_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("perio_exams.id", ondelete="CASCADE"), nullable=False)

    # Location
    tooth_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-32 (universal numbering)
    site: Mapped[str] = mapped_column(String(20), nullable=False)  # DB, B, MB, DL, L, ML

    # Measurements
    probing_depth: Mapped[int] = mapped_column(Integer, nullable=False)  # mm
    recession: Mapped[int] = mapped_column(Integer, default=0)  # mm (positive = recession)
    bleeding_on_probing: Mapped[bool] = mapped_column(Boolean, default=False)
    suppuration: Mapped[bool] = mapped_column(Boolean, default=False)
    plaque: Mapped[bool] = mapped_column(Boolean, default=False)

    # Per-tooth metrics (nullable — only recorded once per tooth, typically on first site)
    furcation_grade: Mapped[int | None] = mapped_column(Integer)  # 0-3
    mobility_grade: Mapped[int | None] = mapped_column(Integer)  # 0-3

    # Relationships
    exam: Mapped["PerioExam"] = relationship(back_populates="readings")

    @hybrid_property
    def clinical_attachment_level(self) -> int:
        """CAL = probing depth + recession."""
        return self.probing_depth + self.recession

    __table_args__ = (
        Index("idx_perio_reading_exam_tooth", "exam_id", "tooth_number"),
        Index("idx_perio_reading_patient", "exam_id"),
    )
