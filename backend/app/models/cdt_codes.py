"""
OrthoFlow AI — CDT Code Library + Multi-Specialty Appointment Types
Full ADA CDT code coverage: D0000-D9999 across all dental specialties.
Additive only — does not modify any existing models.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CDTCode(Base):
    """ADA CDT procedure code — the universal dental procedure classification."""
    __tablename__ = "cdt_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # e.g. "D0120"
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # diagnostic, preventive, restorative, etc.
    subcategory: Mapped[str | None] = mapped_column(String(100))  # e.g. "clinical oral evaluations"
    description: Mapped[str] = mapped_column(Text, nullable=False)  # Official ADA description
    short_description: Mapped[str | None] = mapped_column(String(255))  # Abbreviated for UI
    specialty: Mapped[str] = mapped_column(String(30), nullable=False)  # general, ortho, perio, cosmetic, endo, prosth, surgery
    is_common: Mapped[bool] = mapped_column(Boolean, default=False)  # Frequently used codes surfaced first
    avg_fee: Mapped[int | None] = mapped_column(Integer)  # National average fee in cents (for estimation)
    tooth_specific: Mapped[bool] = mapped_column(Boolean, default=True)  # Whether code applies to specific tooth
    surface_specific: Mapped[bool] = mapped_column(Boolean, default=False)  # Whether code needs surface specification

    __table_args__ = (
        Index("idx_cdt_code", "code", unique=True),
        Index("idx_cdt_category", "category"),
        Index("idx_cdt_specialty", "specialty"),
        Index("idx_cdt_common", "is_common"),
    )


class AppointmentTypeTemplate(Base):
    """Practice-configurable appointment type templates — multi-specialty aware."""
    __tablename__ = "appointment_type_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Prophy/Cleaning", "Crown Prep"
    specialty: Mapped[str] = mapped_column(String(30), nullable=False)  # general, ortho, cosmetic, perio, endo, surgery
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # diagnostic, preventive, restorative, treatment, consultation
    default_duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    default_cdt_codes: Mapped[str | None] = mapped_column(Text)  # Comma-separated default CDT codes for this type
    color: Mapped[str | None] = mapped_column(String(7))  # Hex color for schedule UI
    requires_chair: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_da: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hygiene: Mapped[bool] = mapped_column(Boolean, default=False)  # Hygiene-specific (for recall scheduling)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("idx_appt_type_specialty", "specialty"),
        Index("idx_appt_type_active", "is_active"),
    )
