"""Phase 3 — contract fee type, discount, expected first charges, policy notes, verification.

Adds columns to patient_insurance_contracts for the TC → Contracts workflow. All additive
and nullable / defaulted (no data loss). Patient lifecycle statuses (new_patient, etc.) need
no migration — patients.status is a free String column.

Revision ID: 022
Revises: 021
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa


revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patient_insurance_contracts", sa.Column("fee_type", sa.String(30), server_default="standard", nullable=False))
    op.add_column("patient_insurance_contracts", sa.Column("discount_amount", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("patient_insurance_contracts", sa.Column("expected_first_charges", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("patient_insurance_contracts", sa.Column("policy_notes", sa.Text, nullable=True))
    op.add_column("patient_insurance_contracts", sa.Column("insurance_verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("patient_insurance_contracts", "insurance_verified_at")
    op.drop_column("patient_insurance_contracts", "policy_notes")
    op.drop_column("patient_insurance_contracts", "expected_first_charges")
    op.drop_column("patient_insurance_contracts", "discount_amount")
    op.drop_column("patient_insurance_contracts", "fee_type")
