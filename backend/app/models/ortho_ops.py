"""OrthoFlow — Orthodontic operations models (session: reports/claims/CDT/contracts).

Additive models supporting:
  • Doctor-defined custom CDT codes (practice-scoped)
  • Patient comment sections (info chart + clinical chart)
  • Chart charges attached under the next appointment for checkout collection
  • Per-patient insurance contract (originates from TC Proposal, flows into Claims)
  • Per-(patient×payer) claim billing config: monthly/quarterly, manual/auto, daily poll
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date, Numeric, ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CustomCDTCode(Base):
    """A doctor/practice-defined procedure code (beyond the standard ADA CDT set).

    Practices can create their own codes (e.g., in-house membership plans, custom
    appliances) and represent them however they want, alongside the standard CDT library.
    """
    __tablename__ = "custom_cdt_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "ORTHO-RETAINER-REPL"
    category: Mapped[str] = mapped_column(String(50), default="custom")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(255))
    default_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    medicaid_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_custom_cdt_practice", "practice_id"),
        Index("idx_custom_cdt_code", "practice_id", "code", unique=True),
    )


class PatientComment(Base):
    """Freeform comments on a patient — separated into the info chart and clinical chart.

    `chart` distinguishes: 'info' (front-desk/administrative) vs 'clinical' (DA/doctor).
    """
    __tablename__ = "patient_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    chart: Mapped[str] = mapped_column(String(20), default="info")  # info | clinical
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    author_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_patient_comments_patient_chart", "patient_id", "chart"),
    )


class ChartCharge(Base):
    """A charge queued on a patient's clinical chart under the next appointment to schedule.

    Admin staff collect these at check-out. Attaches a CDT (standard or custom) + fee.
    """
    __tablename__ = "chart_charges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id"))
    cdt_code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tooth_numbers: Mapped[str | None] = mapped_column(String(50))
    is_custom_code: Mapped[bool] = mapped_column(Boolean, default=False)
    # status: queued (added to chart) -> collected (posted to ledger at checkout) -> voided
    status: Mapped[str] = mapped_column(String(20), default="queued")
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    added_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_chart_charges_patient_status", "patient_id", "status"),
        Index("idx_chart_charges_practice", "practice_id"),
    )


class PatientInsuranceContract(Base):
    """Per-patient insurance contract — the accepted TC Proposal that flows into Claims.

    Captures the negotiated treatment fee arrangement (from TC Proposal) plus the billing
    configuration used to generate recurring insurance claims. Editable by Frontdesk/Doctor/TC.
    """
    __tablename__ = "patient_insurance_contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    subscriber_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("insurance_subscribers.id"))
    tc_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # source proposal

    # Financial arrangement (from the accepted proposal)
    total_treatment_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    down_payment: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    insurance_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    patient_portion: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    estimated_months: Mapped[int | None] = mapped_column(Integer)

    # Claim billing configuration (per patient × payer / private)
    payer_kind: Mapped[str] = mapped_column(String(20), default="insurance")  # insurance | private | direct
    billing_cadence: Mapped[str] = mapped_column(String(20), default="monthly")  # monthly | quarterly
    billing_mode: Mapped[str] = mapped_column(String(10), default="auto")  # auto | manual
    claim_destination: Mapped[str] = mapped_column(String(20), default="clearinghouse")  # clearinghouse | private | direct | nctracks
    initial_claim_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # ortho: first claim sent once, then auto
    initial_claim_date: Mapped[date | None] = mapped_column(Date)
    next_claim_due: Mapped[date | None] = mapped_column(Date)
    daily_payment_poll: Mapped[bool] = mapped_column(Boolean, default=True)  # poll payer daily for paid/failed

    status: Mapped[str] = mapped_column(String(20), default="active")  # draft | active | completed | cancelled
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_pic_practice_patient", "practice_id", "patient_id"),
        Index("idx_pic_next_claim_due", "next_claim_due"),
    )


class ClaimPaymentPoll(Base):
    """Daily poll record of a payer's payment status for a contract's recurring claims."""
    __tablename__ = "claim_payment_polls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient_insurance_contracts.id"))
    claim_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("insurance_claims.id"))
    poll_date: Mapped[date] = mapped_column(Date, default=date.today)
    payment_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | paid | failed
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    detail: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_claim_poll_contract", "contract_id", "poll_date"),
    )
