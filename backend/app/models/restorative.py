"""
OrthoFlow AI — Restorative Tooth Charting (Sprint B)
Per-tooth surface-level charting: conditions, existing restorations, planned treatment.
Coexists with the ortho ToothChart model — separate layer, same patient.
"""
import uuid
import enum
from datetime import date, datetime, timezone
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date,
    ForeignKey, Index, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ToothCondition(str, enum.Enum):
    """Conditions that can exist on a tooth."""
    healthy = "healthy"
    caries = "caries"
    fractured = "fractured"
    missing = "missing"
    impacted = "impacted"
    unerupted = "unerupted"
    supernumerary = "supernumerary"
    rotated = "rotated"
    drifted = "drifted"


class RestorationStatus(str, enum.Enum):
    """Status of a restoration entry."""
    existing = "existing"          # Already placed (historical)
    planned = "planned"            # Treatment planned but not done
    in_progress = "in_progress"    # Started (e.g., temp crown)
    completed = "completed"        # Done this visit
    referred = "referred"          # Referred out


class RestorativeChart(Base):
    """Per-patient restorative charting state — conditions + restorations per tooth.

    Stores the overall tooth-level data as JSON for flexibility,
    plus individual restoration records for audit/billing.
    """
    __tablename__ = "restorative_charts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, unique=True)

    # JSON structure per tooth (1-32):
    # { "1": { "condition": "healthy", "mobility": 0, "notes": "" }, ... }
    teeth_conditions: Mapped[dict | None] = mapped_column(JSON, default=dict)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    # Relationships
    restorations: Mapped[list["ToothRestoration"]] = relationship(back_populates="chart")

    __table_args__ = (
        Index("idx_restorative_chart_patient", "patient_id", unique=True),
        Index("idx_restorative_chart_practice", "practice_id"),
    )


class ToothRestoration(Base):
    """Individual restoration record — links to specific tooth + surfaces.

    Each filling, crown, veneer, implant, etc. is a separate record.
    This creates a full treatment history per tooth.
    """
    __tablename__ = "tooth_restorations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chart_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("restorative_charts.id"), nullable=False)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)

    # Location
    tooth_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-32 (universal numbering)
    surfaces: Mapped[str | None] = mapped_column(String(10))  # Combination of M, O, D, B, L, I (e.g., "MOD")

    # What was done
    cdt_code: Mapped[str | None] = mapped_column(String(10))  # e.g., "D2392"
    restoration_type: Mapped[str] = mapped_column(String(50), nullable=False)  # filling, crown, veneer, implant, RCT, extraction, sealant, etc.
    material: Mapped[str | None] = mapped_column(String(50))  # composite, amalgam, porcelain, gold, zirconia, etc.
    status: Mapped[str] = mapped_column(String(20), default="existing")  # existing, planned, in_progress, completed, referred

    # Provider + dates
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    date_placed: Mapped[date | None] = mapped_column(Date)  # When the restoration was done
    date_planned: Mapped[date | None] = mapped_column(Date)  # When it was treatment-planned

    # Notes
    notes: Mapped[str | None] = mapped_column(Text)
    lab_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appliance_prescriptions.id"))  # Links to lab tracking if applicable

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    chart: Mapped["RestorativeChart"] = relationship(back_populates="restorations")

    __table_args__ = (
        Index("idx_restoration_patient_tooth", "patient_id", "tooth_number"),
        Index("idx_restoration_chart", "chart_id"),
        Index("idx_restoration_status", "practice_id", "status"),
    )
