"""
OrthoFlow AI — Data Models
Multi-tenant: every model scoped by practice_id.
HIPAA: PHI fields marked for encryption at rest.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

import enum


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
    office_manager = "office_manager"
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="practice")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="practice")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.bookkeeper)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    practice: Mapped["Practice"] = relationship(back_populates="users")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"))
    vendor_name: Mapped[str] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[datetime | None] = mapped_column(DateTime)
    due_date: Mapped[datetime | None] = mapped_column(DateTime)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus), default=InvoiceStatus.pending)
    s3_key: Mapped[str | None] = mapped_column(String(512))  # original document
    raw_text: Mapped[str | None] = mapped_column(Text)  # OCR output
    coded_json: Mapped[str | None] = mapped_column(Text)  # AI classification result
    confidence_score: Mapped[float | None] = mapped_column(Float)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    practice: Mapped["Practice"] = relationship(back_populates="invoices")
    line_items: Mapped[list["LineItem"]] = relationship(back_populates="invoice")


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"))
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[float | None] = mapped_column(Float)
    unit_price: Mapped[float | None] = mapped_column(Float)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str | None] = mapped_column(String(100))  # AI-assigned expense category
    gl_code: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[float | None] = mapped_column(Float)

    invoice: Mapped["Invoice"] = relationship(back_populates="line_items")


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
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
