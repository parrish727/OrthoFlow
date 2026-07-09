"""
OrthoFlow AI — Clinical Data Models (Phase 1)
Scheduling, patient charts, DA assignments, treatment notes, tooth charting.
Multi-tenant: all models scoped by practice_id.
"""
import uuid
import enum
from datetime import datetime, date, time, timezone
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date, Time,
    ForeignKey, Enum as SAEnum, Numeric, Index, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ─────────────────────────────────────────────────────────────────────

class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    checked_in = "checked_in"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class TreatmentPhase(str, enum.Enum):
    consultation = "consultation"
    records = "records"
    bonding = "bonding"
    active = "active"
    finishing = "finishing"
    retention = "retention"
    complete = "complete"


class PatientStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    prospective = "prospective"
    transferred = "transferred"


# ── Models ────────────────────────────────────────────────────────────────────

class Patient(Base):
    """Core patient record — demographics and treatment status."""
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    phone_secondary: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PatientStatus] = mapped_column(SAEnum(PatientStatus), default=PatientStatus.active)
    treatment_phase: Mapped[TreatmentPhase] = mapped_column(SAEnum(TreatmentPhase), default=TreatmentPhase.consultation)
    referring_doctor: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)  # General patient notes (non-clinical)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")
    treatment_notes: Mapped[list["TreatmentNote"]] = relationship(back_populates="patient")
    tooth_chart: Mapped["ToothChart | None"] = relationship(back_populates="patient", uselist=False)

    __table_args__ = (
        Index("idx_patients_practice_id", "practice_id"),
        Index("idx_patients_practice_name", "practice_id", "last_name", "first_name"),
        Index("idx_patients_practice_status", "practice_id", "status"),
    )


class Chair(Base):
    """Treatment chairs/operatories in a practice."""
    __tablename__ = "chairs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "Chair 1", "Op A"
    color: Mapped[str | None] = mapped_column(String(7))  # hex color for UI
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="chair")

    __table_args__ = (
        Index("idx_chairs_practice_id", "practice_id"),
    )


class DentalAssistant(Base):
    """Dental assistants available for scheduling assignment."""
    __tablename__ = "dental_assistants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # links to user account if they have one
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))  # hex color for schedule UI
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="dental_assistant")

    __table_args__ = (
        Index("idx_da_practice_id", "practice_id"),
    )


class Appointment(Base):
    """Scheduled appointment — links patient, chair, and DA."""
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    chair_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chairs.id"))
    da_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("dental_assistants.id"))
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[AppointmentStatus] = mapped_column(SAEnum(AppointmentStatus), default=AppointmentStatus.scheduled)
    appointment_type: Mapped[str | None] = mapped_column(String(100))  # e.g. "Adjustment", "Bonding", "Consultation"
    procedure_codes: Mapped[str | None] = mapped_column(Text)  # comma-separated CDT codes
    notes: Mapped[str | None] = mapped_column(Text)  # appointment-specific notes
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    chair: Mapped["Chair | None"] = relationship(back_populates="appointments")
    dental_assistant: Mapped["DentalAssistant | None"] = relationship(back_populates="appointments")
    treatment_notes: Mapped[list["TreatmentNote"]] = relationship(back_populates="appointment")

    __table_args__ = (
        Index("idx_appt_practice_date", "practice_id", "appointment_date"),
        Index("idx_appt_patient", "patient_id", "appointment_date"),
        Index("idx_appt_chair_date", "chair_id", "appointment_date"),
        Index("idx_appt_da_date", "da_id", "appointment_date"),
        Index("idx_appt_practice_status", "practice_id", "status"),
    )


class TreatmentNote(Base):
    """Clinical notes per appointment or per patient."""
    __tablename__ = "treatment_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id"))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text)  # AI-generated summary of dictated note
    note_type: Mapped[str] = mapped_column(String(50), default="clinical")  # clinical, progress, referral
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="treatment_notes")
    appointment: Mapped["Appointment | None"] = relationship(back_populates="treatment_notes")

    __table_args__ = (
        Index("idx_notes_patient", "patient_id", "created_at"),
        Index("idx_notes_appointment", "appointment_id"),
    )


class ToothChart(Base):
    """Per-patient orthodontic tooth chart state. Stores bracket placement, wires, bands as JSON."""
    __tablename__ = "tooth_charts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, unique=True)

    # JSON structure for each tooth (1-32):
    # {"1": {"bracket": "metal", "wire": "16NiTi", "band": false, "condition": "healthy", "notes": ""}, ...}
    teeth_data: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # Arch wire tracking
    upper_wire: Mapped[str | None] = mapped_column(String(100))  # e.g. "16 NiTi", "18 SS"
    lower_wire: Mapped[str | None] = mapped_column(String(100))
    upper_wire_date: Mapped[date | None] = mapped_column(Date)
    lower_wire_date: Mapped[date | None] = mapped_column(Date)

    # Appliances
    appliances: Mapped[dict | None] = mapped_column(JSON, default=list)  # [{"type": "expander", "placed": "2026-01-15", "notes": ""}]

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    patient: Mapped["Patient"] = relationship(back_populates="tooth_chart")

    __table_args__ = (
        Index("idx_tooth_chart_patient", "patient_id", unique=True),
    )
