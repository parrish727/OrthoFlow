"""
OrthoFlow AI — Patient Portal, Reporting, and Migration Models.
"""
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Patient Portal ────────────────────────────────────────────────────────────

class PortalAccount(Base):
    """Patient login account — separate from staff users."""
    __tablename__ = "portal_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(100))
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_portal_accounts_email", "practice_id", "email", unique=True),
        Index("idx_portal_accounts_patient", "patient_id", unique=True),
    )


class PortalForm(Base):
    """Configurable forms (intake, consent, health history)."""
    __tablename__ = "portal_forms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    form_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_required_new_patient: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_portal_forms_practice", "practice_id", "form_type"),
    )


class PortalFormSubmission(Base):
    """Patient-submitted form responses."""
    __tablename__ = "portal_form_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    form_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portal_forms.id"), nullable=False)
    responses: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_form_submissions_patient", "patient_id"),
        Index("idx_form_submissions_practice", "practice_id", "status"),
    )


class PortalMessage(Base):
    """Patient ↔ office secure messaging."""
    __tablename__ = "portal_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_by_staff: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_portal_messages_patient", "patient_id", "created_at"),
        Index("idx_portal_messages_unread", "practice_id", "direction", "is_read"),
    )


# ── Reporting ─────────────────────────────────────────────────────────────────

class ReportSnapshot(Base):
    """Cached monthly report data for fast retrieval."""
    __tablename__ = "report_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (
        Index("idx_report_snapshots_practice", "practice_id", "report_type", "period_start"),
    )


# ── Migration ─────────────────────────────────────────────────────────────────

class MigrationJob(Base):
    """Tracks a patient data import from another PMS."""
    __tablename__ = "migration_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    imported_records: Mapped[int] = mapped_column(Integer, default=0)
    failed_records: Mapped[int] = mapped_column(Integer, default=0)
    skipped_records: Mapped[int] = mapped_column(Integer, default=0)
    field_mapping: Mapped[dict | None] = mapped_column(JSONB)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB)
    import_log: Mapped[str | None] = mapped_column(Text)
    source_file_path: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_migration_jobs_practice", "practice_id", "status"),
    )
