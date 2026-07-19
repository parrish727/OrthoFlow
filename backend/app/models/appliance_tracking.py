"""
OrthoFlow AI — Lab Appliance Tracking Models (Sprint 4)
Full lifecycle: prescription → sent to lab → fabricating → shipped → received → placed
Multi-tenant: all models scoped by practice_id.
"""
import uuid
import enum
from datetime import date, datetime, timezone
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date,
    ForeignKey, Enum as SAEnum, Numeric, Index, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ─────────────────────────────────────────────────────────────────────

class ApplianceType(str, enum.Enum):
    """Types of orthodontic appliances ordered from labs."""
    expander = "expander"                 # RPE, Hyrax, Haas
    retainer = "retainer"                 # Hawley, Essix, fixed
    aligner = "aligner"                   # Clear aligner trays
    space_maintainer = "space_maintainer" # Band and loop, Nance, TPA
    herbst = "herbst"                     # Herbst appliance
    mara = "mara"                         # MARA appliance
    headgear = "headgear"                 # Cervical pull, high pull
    splint = "splint"                     # Bite splints, night guards
    positioner = "positioner"             # Tooth positioner
    spring_aligner = "spring_aligner"     # Spring aligner
    habit_breaker = "habit_breaker"       # Tongue crib, thumb guard
    surgical_splint = "surgical_splint"   # Surgical stents
    indirect_bond_tray = "indirect_bond_tray"  # IDB trays
    other = "other"


class ApplianceStatus(str, enum.Enum):
    """Lifecycle status of a lab appliance order."""
    draft = "draft"                 # Prescription started but not sent
    submitted = "submitted"         # Sent to lab
    received_by_lab = "received_by_lab"  # Lab acknowledged receipt
    in_fabrication = "in_fabrication"    # Lab actively making it
    shipped = "shipped"             # Lab shipped to practice
    received = "received"           # Practice received the appliance
    quality_check = "quality_check" # Practice checking fit/quality
    placed = "placed"               # Appliance placed on patient
    rejected = "rejected"           # Rejected — needs remake
    cancelled = "cancelled"         # Order cancelled


class Arch(str, enum.Enum):
    """Which arch the appliance is for."""
    upper = "upper"
    lower = "lower"
    both = "both"


# ── Models ────────────────────────────────────────────────────────────────────

class Lab(Base):
    """Lab vendor that fabricates appliances for the practice."""
    __tablename__ = "labs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(512))
    account_number: Mapped[str | None] = mapped_column(String(100))  # Practice's account # with the lab
    avg_turnaround_days: Mapped[int] = mapped_column(Integer, default=10)  # Average business days
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    prescriptions: Mapped[list["AppliancePrescription"]] = relationship(back_populates="lab")

    __table_args__ = (
        Index("idx_labs_practice_id", "practice_id"),
        Index("idx_labs_practice_active", "practice_id", "is_active"),
    )


class AppliancePrescription(Base):
    """An appliance order/prescription sent to a lab for a patient."""
    __tablename__ = "appliance_prescriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    lab_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("labs.id"), nullable=False)
    prescribed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Appliance details
    appliance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    appliance_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Free-text specific name
    arch: Mapped[str] = mapped_column(String(10), nullable=False)  # upper, lower, both
    teeth: Mapped[str | None] = mapped_column(String(100))  # Specific teeth (e.g. "3-14" or "19,20,21")
    color: Mapped[str | None] = mapped_column(String(100))  # Patient's color choice if applicable
    material: Mapped[str | None] = mapped_column(String(100))  # e.g. "Acrylic", "Metal", "Clear"

    # Prescription notes and details
    rx_notes: Mapped[str | None] = mapped_column(Text)  # Clinical notes for the lab
    special_instructions: Mapped[str | None] = mapped_column(Text)  # Special lab instructions
    scan_file_url: Mapped[str | None] = mapped_column(String(512))  # Link to intraoral scan file in MinIO

    # Status tracking
    status: Mapped[str] = mapped_column(String(30), default="draft")
    priority: Mapped[str] = mapped_column(String(10), default="normal")  # normal, rush, emergency

    # Date tracking
    date_prescribed: Mapped[date] = mapped_column(Date, nullable=False)
    date_sent_to_lab: Mapped[date | None] = mapped_column(Date)
    date_received_by_lab: Mapped[date | None] = mapped_column(Date)
    date_shipped: Mapped[date | None] = mapped_column(Date)
    date_received: Mapped[date | None] = mapped_column(Date)
    date_placed: Mapped[date | None] = mapped_column(Date)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date)

    # Tracking info
    tracking_number: Mapped[str | None] = mapped_column(String(100))
    lab_case_number: Mapped[str | None] = mapped_column(String(100))  # Lab's internal case ID

    # Quality / rejection tracking
    is_remake: Mapped[bool] = mapped_column(Boolean, default=False)
    remake_reason: Mapped[str | None] = mapped_column(Text)
    original_prescription_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appliance_prescriptions.id"))

    # Cost tracking
    lab_fee: Mapped[float | None] = mapped_column(Numeric(10, 2))
    rush_fee: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    lab: Mapped["Lab"] = relationship(back_populates="prescriptions")
    status_history: Mapped[list["ApplianceStatusHistory"]] = relationship(back_populates="prescription")

    __table_args__ = (
        Index("idx_rx_practice_id", "practice_id"),
        Index("idx_rx_patient_id", "patient_id"),
        Index("idx_rx_lab_id", "lab_id"),
        Index("idx_rx_practice_status", "practice_id", "status"),
        Index("idx_rx_practice_expected", "practice_id", "expected_delivery_date"),
    )


class ApplianceStatusHistory(Base):
    """Audit trail of status changes for an appliance prescription."""
    __tablename__ = "appliance_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appliance_prescriptions.id"), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    prescription: Mapped["AppliancePrescription"] = relationship(back_populates="status_history")

    __table_args__ = (
        Index("idx_status_history_rx", "prescription_id", "changed_at"),
    )


class EasyRxIntegration(Base):
    """EasyRx integration settings per practice (SSO launch-link + patient sync)."""
    __tablename__ = "easyrx_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False, unique=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    easyrx_practice_id: Mapped[str | None] = mapped_column(String(100))  # EasyRx's practice identifier
    easyrx_api_key: Mapped[str | None] = mapped_column(String(255))  # Encrypted at rest
    launch_url: Mapped[str | None] = mapped_column(String(512))  # SSO launch URL template
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_easyrx_practice", "practice_id", unique=True),
    )
