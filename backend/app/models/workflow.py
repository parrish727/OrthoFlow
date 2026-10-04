"""
OrthoFlow AI — Sprint 2 Workflow Models.
Patient visit tracking, recent searches, patient documents.
Multi-tenant: all models scoped by practice_id.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Text, BigInteger, Boolean, DateTime, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PatientVisitStatus(Base):
    """Tracks patient flow through the office: lobby → seated → checked_out → dismissed."""
    __tablename__ = "patient_visit_status"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="lobby")
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
    """Scanned documents, consent forms, referral letters, and office⇄patient file exchange.

    One row == one object in the private 'orthoflow-documents' MinIO bucket (via storage_key).
    The SAME row is surfaced in the OrthoFlow chart, the OrthoFlow Documents view, and MyOrthoChart
    — never copied. Files are ClamAV-scanned before the row is written (scan_status='clean').

    direction: office_to_patient | patient_to_office
    uploaded_by_type: staff | patient
    """
    __tablename__ = "patient_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # Legacy external reference (kept for backward compatibility with pre-028 rows). New uploads
    # use storage_key + presigned URLs and leave file_url NULL.
    file_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Object key in the private documents bucket: practice_id/patient_id/<uuid>.<ext>
    storage_key: Mapped[str | None] = mapped_column(String(512))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    # Who/what uploaded it. uploaded_by is NULL for patient uploads (no staff user).
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_by_type: Mapped[str] = mapped_column(String(10), nullable=False, default="staff")
    direction: Mapped[str] = mapped_column(String(20), nullable=False, default="office_to_patient")
    shared_with_patient: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scan_status: Mapped[str] = mapped_column(String(20), nullable=False, default="clean")
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_documents_patient", "patient_id"),
    )


class DocumentNotification(Base):
    """In-app notification feed for document exchange, synced across OrthoFlow and MyOrthoChart.

    Modeled on AppointmentNotification. One upload creates one notification for the OTHER side:
      • office uploads a doc  -> audience='patient' (shown in MyOrthoChart)
      • patient uploads a doc -> audience='office'  (shown to staff in OrthoFlow)

    kind: document_uploaded
    """
    __tablename__ = "document_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient_documents.id", ondelete="CASCADE"), nullable=False)
    audience: Mapped[str] = mapped_column(String(10), nullable=False, default="patient")
    kind: Mapped[str] = mapped_column(String(30), nullable=False, default="document_uploaded")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    action_url: Mapped[str | None] = mapped_column(String(300))
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_doc_notif_patient", "practice_id", "patient_id", "audience"),
        Index("idx_doc_notif_document", "document_id"),
    )
