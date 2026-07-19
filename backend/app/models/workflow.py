"""
OrthoFlow AI — Sprint 2 Workflow Models.
Patient visit tracking, recent searches, patient documents.
Multi-tenant: all models scoped by practice_id.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Text, BigInteger, DateTime, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PatientVisitStatus(Base):
    """Tracks patient flow through the office: waiting → seated → in_treatment → checked_out."""
    __tablename__ = "patient_visit_status"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting")
    chair_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chairs.id"), nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_visit_status_practice_status", "practice_id", "status"),
        Index("idx_visit_status_appointment", "appointment_id"),
    )


class RecentPatientSearch(Base):
    """Tracks user's recently viewed/searched patients for quick access."""
    __tablename__ = "recent_patient_searches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    searched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_recent_searches_user_time", "user_id", searched_at.desc()),
        UniqueConstraint("user_id", "patient_id", name="uq_recent_searches_user_patient"),
    )


class PatientDocument(Base):
    """Scanned documents, consent forms, referral letters linked to a patient chart."""
    __tablename__ = "patient_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_documents_patient", "patient_id"),
    )
