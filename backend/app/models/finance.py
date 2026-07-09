"""
OrthoFlow AI — Phase 2 Finance & Insurance Models.
Patient ledger, insurance subscribers, claim line items, payment postings.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date, Numeric,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InsuranceSubscriber(Base):
    """Links a patient to their insurance plan with benefit tracking."""
    __tablename__ = "insurance_subscribers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    relationship: Mapped[str] = mapped_column(String(20), default="self")
    subscriber_id: Mapped[str] = mapped_column(String(50), nullable=False)
    group_number: Mapped[str | None] = mapped_column(String(50))
    payer_id: Mapped[str] = mapped_column(String(50), nullable=False)
    payer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    plan_name: Mapped[str | None] = mapped_column(String(200))
    plan_type: Mapped[str] = mapped_column(String(20), default="commercial")
    coverage_type: Mapped[str] = mapped_column(String(20), default="primary")
    subscriber_first_name: Mapped[str | None] = mapped_column(String(100))
    subscriber_last_name: Mapped[str | None] = mapped_column(String(100))
    subscriber_dob: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    termination_date: Mapped[date | None] = mapped_column(Date)
    copay_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    deductible_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    deductible_met: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    annual_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    annual_used: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    ortho_lifetime_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ortho_lifetime_used: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    ortho_coverage_pct: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_eligibility_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eligibility_status: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_ins_sub_practice_patient", "practice_id", "patient_id"),
        Index("idx_ins_sub_subscriber_id", "subscriber_id"),
    )


class PatientLedgerEntry(Base):
    """Financial transaction on a patient account — charges, payments, adjustments."""
    __tablename__ = "patient_ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)  # charge, payment, adjustment, credit, refund
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    running_balance: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cdt_code: Mapped[str | None] = mapped_column(String(10))
    tooth_numbers: Mapped[str | None] = mapped_column(String(50))
    claim_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("insurance_claims.id"))
    payment_posting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    provider_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    service_date: Mapped[date | None] = mapped_column(Date)
    posted_date: Mapped[date] = mapped_column(Date, default=date.today)
    payment_method: Mapped[str | None] = mapped_column(String(20))
    reference_number: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_ledger_practice_patient", "practice_id", "patient_id"),
        Index("idx_ledger_patient_date", "patient_id", "posted_date"),
        Index("idx_ledger_claim", "claim_id"),
        Index("idx_ledger_entry_type", "practice_id", "entry_type"),
    )


class ClaimLineItem(Base):
    """Individual procedure line on an insurance claim."""
    __tablename__ = "claim_line_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("insurance_claims.id", ondelete="CASCADE"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    cdt_code: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    tooth_numbers: Mapped[str | None] = mapped_column(String(50))
    surface: Mapped[str | None] = mapped_column(String(10))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    billed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    allowed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    adjustment_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    patient_responsibility: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    denial_code: Mapped[str | None] = mapped_column(String(20))
    denial_reason: Mapped[str | None] = mapped_column(String(300))
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_claim_lines_claim", "claim_id"),
    )


class PaymentPosting(Base):
    """ERA/835 batch payment or manual payment posting from a payer."""
    __tablename__ = "payment_postings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    payer_name: Mapped[str | None] = mapped_column(String(200))
    check_number: Mapped[str | None] = mapped_column(String(50))
    check_date: Mapped[date | None] = mapped_column(Date)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    applied_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    unapplied_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    era_trace_number: Mapped[str | None] = mapped_column(String(50))
    era_data: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    posted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    posted_date: Mapped[date] = mapped_column(Date, default=date.today)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_payment_posting_practice", "practice_id"),
        Index("idx_payment_posting_status", "practice_id", "status"),
        Index("idx_payment_posting_era", "era_trace_number"),
    )
