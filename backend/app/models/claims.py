"""
OrthoFlow AI — Insurance Claims Models (v2.1)
Medicare/Medicaid claims lifecycle management.
"""
import uuid
import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Text, Numeric, Integer, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class ClaimStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    accepted = "accepted"
    rejected = "rejected"
    paid = "paid"
    denied = "denied"
    appealed = "appealed"


class PayerType(str, enum.Enum):
    medicare = "medicare"
    medicaid = "medicaid"
    commercial = "commercial"


class AuthStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    denied = "denied"
    expired = "expired"


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    patient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    subscriber_id: Mapped[str] = mapped_column(String(50), nullable=False)
    payer_id: Mapped[str] = mapped_column(String(50), nullable=False)
    payer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    state_code: Mapped[str | None] = mapped_column(String(2))
    claim_number: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    cdt_codes: Mapped[dict] = mapped_column(JSONB, default=list)
    total_billed: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_allowed: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total_paid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    patient_responsibility: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    prior_auth_number: Mapped[str | None] = mapped_column(String(50))
    rendering_provider_npi: Mapped[str] = mapped_column(String(10), nullable=False)
    billing_provider_npi: Mapped[str] = mapped_column(String(10), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    submission_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    adjudication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    denial_codes: Mapped[dict | None] = mapped_column(JSONB)
    denial_reason: Mapped[str | None] = mapped_column(Text)
    era_reference: Mapped[str | None] = mapped_column(String(50))
    coordination_of_benefits: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("payer_type IN ('medicare', 'medicaid', 'commercial')", name="ck_claim_payer_type"),
        CheckConstraint("status IN ('draft','submitted','accepted','rejected','paid','denied','appealed')", name="ck_claim_status"),
    )


class PriorAuthorization(Base):
    __tablename__ = "prior_authorizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    payer_id: Mapped[str] = mapped_column(String(50), nullable=False)
    auth_number: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    treatment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cdt_codes: Mapped[dict] = mapped_column(JSONB, default=list)
    clinical_notes: Mapped[str] = mapped_column(Text, nullable=False)
    diagnostic_codes: Mapped[dict] = mapped_column(JSONB, default=list)
    requested_date: Mapped[date] = mapped_column(Date, nullable=False)
    approved_date: Mapped[date | None] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date)
    approved_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    denial_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class PracticePayerConfig(Base):
    __tablename__ = "practice_payer_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("practices.id"), nullable=False)
    payer_id: Mapped[str] = mapped_column(String(50), nullable=False)
    payer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    payer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    state_code: Mapped[str | None] = mapped_column(String(2))
    enrolled: Mapped[bool] = mapped_column(default=False)
    npi: Mapped[str] = mapped_column(String(10), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(20), nullable=False)
    clearinghouse: Mapped[str] = mapped_column(String(50), nullable=False)
    clearinghouse_id: Mapped[str] = mapped_column(String(50), nullable=False)
    fee_schedule: Mapped[dict | None] = mapped_column(JSONB)
    submission_method: Mapped[str] = mapped_column(String(20), default="electronic")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
