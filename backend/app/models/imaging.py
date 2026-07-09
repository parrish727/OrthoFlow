"""
OrthoFlow AI — Phase 4a Imaging Suite Models.
Patient images, imaging series, overdue alerts.
Architected for Phase 4b edge appliance DICOM ingest.
"""
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import (
    String, Text, Integer, BigInteger, Boolean, DateTime, Date,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ImagingSeries(Base):
    """Groups related images (e.g. full-mouth series, initial records set)."""
    __tablename__ = "imaging_series"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id"))
    series_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    captured_date: Mapped[date] = mapped_column(Date, nullable=False)
    captured_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_series_practice_patient", "practice_id", "patient_id"),
        Index("idx_series_date", "patient_id", "captured_date"),
    )


class PatientImage(Base):
    """Individual image file — radiograph, photo, or CBCT slice."""
    __tablename__ = "patient_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    series_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("imaging_series.id"))
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id"))
    # Image classification
    image_type: Mapped[str] = mapped_column(String(30), nullable=False)
    modality: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(300))
    tooth_numbers: Mapped[str | None] = mapped_column(String(50))
    # Storage
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(100), default="orthoflow-imaging")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    content_type: Mapped[str | None] = mapped_column(String(100))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    # DICOM metadata (for 4b edge appliance)
    dicom_study_uid: Mapped[str | None] = mapped_column(String(128))
    dicom_series_uid: Mapped[str | None] = mapped_column(String(128))
    dicom_instance_uid: Mapped[str | None] = mapped_column(String(128))
    dicom_metadata: Mapped[dict | None] = mapped_column(JSONB)
    # Source tracking (4b hook)
    source: Mapped[str] = mapped_column(String(20), default="upload")
    source_device_id: Mapped[str | None] = mapped_column(String(100))
    source_device_name: Mapped[str | None] = mapped_column(String(200))
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")
    captured_date: Mapped[date] = mapped_column(Date, nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_images_practice_patient", "practice_id", "patient_id"),
        Index("idx_images_patient_type", "patient_id", "image_type"),
        Index("idx_images_patient_date", "patient_id", "captured_date"),
        Index("idx_images_series", "series_id"),
        Index("idx_images_dicom_study", "dicom_study_uid"),
        Index("idx_images_source_device", "source_device_id"),
    )


class ImagingAlert(Base):
    """Overdue imaging alerts — tracks when patients need new images."""
    __tablename__ = "imaging_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    image_type: Mapped[str] = mapped_column(String(30), nullable=False)
    last_taken_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    treatment_phase: Mapped[str | None] = mapped_column(String(20))
    rule_description: Mapped[str | None] = mapped_column(String(200))
    dismissed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_image_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patient_images.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_alerts_practice_status", "practice_id", "status"),
        Index("idx_alerts_patient", "patient_id"),
        Index("idx_alerts_due_date", "due_date", "status"),
    )
