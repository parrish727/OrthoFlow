"""
OrthoFlow AI — Data Models
Multi-tenant: every model scoped by practice_id.
HIPAA: PHI fields marked for encryption at rest.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

import enum


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    coded = "coded"
    review = "review"
    approved = "approved"
    paid = "paid"
    rejected = "rejected"


class UserRole(str, enum.Enum):
    owner = "owner"
    doctor = "doctor"
    office_manager = "office_manager"
    dental_assistant = "dental_assistant"
    front_desk = "front_desk"
    bookkeeper = "bookkeeper"


class Practice(Base):
    __tablename__ = "practices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    npi: Mapped[str | None] = mapped_column(String(20))  # National Provider Identifier
    address: Mapped[str | None] = mapped_column(Text)
    tier: Mapped[str] = mapped_column(String(20), default="standard")  # standard | enterprise
    logo_url: Mapped[str | None] = mapped_column(String(512))
    primary_color: Mapped[str | None] = mapped_column(String(7))  # hex color
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="practice")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="practice")
    integrations: Mapped[list["Integration"]] = relationship(back_populates="practice")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="bookkeeper")
    phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    practice: Mapped["Practice"] = relationship(back_populates="users")

    __table_args__ = (
        Index("idx_users_practice_id", "practice_id"),
        Index("idx_users_email", "email"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"))
    vendor_name: Mapped[str] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus), default=InvoiceStatus.pending)
    s3_key: Mapped[str | None] = mapped_column(String(512))  # original document
    raw_text: Mapped[str | None] = mapped_column(Text)  # OCR output
    coded_json: Mapped[str | None] = mapped_column(Text)  # AI classification result
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3))  # 0.000 to 1.000
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    practice: Mapped["Practice"] = relationship(back_populates="invoices")
    line_items: Mapped[list["LineItem"]] = relationship(back_populates="invoice")

    __table_args__ = (
        Index("idx_invoices_practice_status", "practice_id", "status"),
        Index("idx_invoices_practice_created", "practice_id", "created_at"),
    )


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"))
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    unit_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    category: Mapped[str | None] = mapped_column(String(100))  # AI-assigned expense category
    gl_code: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))

    invoice: Mapped["Invoice"] = relationship(back_populates="line_items")

    __table_args__ = (
        Index("idx_line_items_invoice_id", "invoice_id"),
    )


class AuditLog(Base):
    """HIPAA-required audit trail for all data access and modifications."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))  # e.g. "invoice.view", "invoice.approve"
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_audit_practice_timestamp", "practice_id", "timestamp"),
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
    )


class Integration(Base):
    """Stores OAuth tokens and integration credentials per practice (replaces in-memory/NPI abuse)."""
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"))
    provider: Mapped[str] = mapped_column(String(50))  # "quickbooks", "plaid", "ortho2"
    access_token: Mapped[str | None] = mapped_column(Text)  # encrypted
    refresh_token: Mapped[str | None] = mapped_column(Text)  # encrypted
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    realm_id: Mapped[str | None] = mapped_column(String(100))  # QBO company ID
    config_json: Mapped[str | None] = mapped_column(Text)  # provider-specific settings (e.g. account mappings)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    practice: Mapped["Practice"] = relationship(back_populates="integrations")

    __table_args__ = (
        Index("idx_integrations_practice_provider", "practice_id", "provider", unique=True),
    )


class OtpCode(Base):
    """Persistent OTP storage (replaces in-memory dict)."""
    __tablename__ = "otp_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    code: Mapped[str] = mapped_column(String(6))
    phone: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_otp_user_expires", "user_id", "expires_at"),
    )
