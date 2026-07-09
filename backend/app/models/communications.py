"""
OrthoFlow AI — Phase 3 Patient Communications Models.
Preferences, message templates, message log, scheduled messages.
"""
import uuid
from datetime import datetime, date, time, timezone
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date, Time,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CommunicationPreference(Base):
    """Per-patient communication preferences and TCPA consent tracking."""
    __tablename__ = "communication_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, unique=True)
    # Channel preferences
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_channel: Mapped[str] = mapped_column(String(10), default="sms")
    phone_number: Mapped[str | None] = mapped_column(String(20))
    email_address: Mapped[str | None] = mapped_column(String(255))
    # Reminder preferences
    reminder_24hr: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_2hr: Mapped[bool] = mapped_column(Boolean, default=True)
    recall_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    birthday_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    # Quiet hours
    quiet_start: Mapped[time | None] = mapped_column(Time)
    quiet_end: Mapped[time | None] = mapped_column(Time)
    # TCPA
    tcpa_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    tcpa_consent_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tcpa_consent_method: Mapped[str | None] = mapped_column(String(50))
    tcpa_opt_out_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_comm_prefs_practice_patient", "practice_id", "patient_id", unique=True),
    )


class MessageTemplate(Base):
    """Reusable message templates with variable substitution."""
    __tablename__ = "message_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    template_type: Mapped[str] = mapped_column(String(30), nullable=False)
    channel: Mapped[str] = mapped_column(String(10), default="sms")
    subject: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    send_timing: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_msg_templates_practice", "practice_id", "template_type"),
    )


class MessageLog(Base):
    """All sent and received messages — delivery tracking."""
    __tablename__ = "message_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id"))
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # outbound, inbound
    channel: Mapped[str] = mapped_column(String(10), nullable=False)
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)
    from_address: Mapped[str | None] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("message_templates.id"))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    external_id: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(String(500))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reply_body: Mapped[str | None] = mapped_column(Text)
    metadata: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_msg_log_practice_patient", "practice_id", "patient_id"),
        Index("idx_msg_log_status", "practice_id", "status"),
        Index("idx_msg_log_appointment", "appointment_id"),
        Index("idx_msg_log_created", "practice_id", "created_at"),
        Index("idx_msg_log_external_id", "external_id"),
    )


class ScheduledMessage(Base):
    """Queued messages scheduled for future delivery."""
    __tablename__ = "scheduled_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id"))
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("message_templates.id"))
    channel: Mapped[str] = mapped_column(String(10), nullable=False)
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(String(500))
    cancelled_reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_scheduled_msg_due", "scheduled_for", "status"),
        Index("idx_scheduled_msg_appointment", "appointment_id"),
        Index("idx_scheduled_msg_patient", "patient_id"),
    )
