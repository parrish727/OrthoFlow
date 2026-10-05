"""Ledger AR enhancements — per-patient AR/collections note (surfaced in the Ledger roster).

Revision ID: 029
Revises: 028
Create Date: 2026-10-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("ar_note", sa.Text, nullable=True))
    op.add_column("patients", sa.Column("ar_note_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("patients", sa.Column("ar_note_updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("patients", "ar_note_updated_by")
    op.drop_column("patients", "ar_note_updated_at")
    op.drop_column("patients", "ar_note")
