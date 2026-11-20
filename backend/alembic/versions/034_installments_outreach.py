"""Payment plan installments (ledger due dates), AR outreach events, practice auto-outreach flag.

Revision ID: 034
Revises: 033
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_plan_installments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("patient_insurance_contracts.id"), nullable=True),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("canceled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_installment_patient_due", "payment_plan_installments", ["practice_id", "patient_id", "due_date"])
    op.create_index("idx_installment_contract", "payment_plan_installments", ["contract_id"])

    op.create_table(
        "ar_outreach_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("milestone_days", sa.Integer, nullable=False),
        sa.Column("anchor_due_date", sa.Date, nullable=False),
        sa.Column("channel", sa.String(10), nullable=False, server_default="sms"),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("message_log_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("uq_ar_outreach_cycle", "ar_outreach_events", ["patient_id", "milestone_days", "anchor_due_date"], unique=True)
    op.create_index("idx_ar_outreach_practice", "ar_outreach_events", ["practice_id", "created_at"])

    op.add_column("practices", sa.Column("ar_auto_outreach_enabled", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("practices", sa.Column("ar_auto_outreach_enabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("practices", sa.Column("ar_auto_outreach_enabled_by", UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("practices", "ar_auto_outreach_enabled_by")
    op.drop_column("practices", "ar_auto_outreach_enabled_at")
    op.drop_column("practices", "ar_auto_outreach_enabled")
    op.drop_table("ar_outreach_events")
    op.drop_table("payment_plan_installments")
