"""Insurance lifetime-benefit rework — period tracking + archive table.

Ortho benefit is a LIFETIME maximum (no co-pay). Adds benefit-period tracking to
insurance_subscribers and an insurance_benefit_periods archive table so a reset
(new job / new insurer / plan change) archives the prior period for audit history.
The legacy copay_amount / annual_* columns are intentionally LEFT in place (no data
loss); the ortho UI and eligibility simply stop surfacing co-pay and relabel the
remaining figure as "remaining benefit".

Revision ID: 021
Revises: 020
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("insurance_subscribers", sa.Column("benefit_period_started", sa.Date, nullable=True))
    op.add_column("insurance_subscribers", sa.Column("benefit_reset_reason", sa.String(50), nullable=True))

    op.create_table(
        "insurance_benefit_periods",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("subscriber_id", UUID(as_uuid=True), sa.ForeignKey("insurance_subscribers.id"), nullable=False),
        sa.Column("payer_name", sa.String(200)),
        sa.Column("plan_name", sa.String(200)),
        sa.Column("lifetime_max", sa.Numeric(10, 2)),
        sa.Column("lifetime_used", sa.Numeric(10, 2), server_default="0"),
        sa.Column("coverage_pct", sa.Integer),
        sa.Column("period_started", sa.Date),
        sa.Column("period_ended", sa.Date, server_default=sa.func.current_date()),
        sa.Column("reset_reason", sa.String(50)),
        sa.Column("archived_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_benefit_period_patient", "insurance_benefit_periods", ["practice_id", "patient_id"])
    op.create_index("idx_benefit_period_subscriber", "insurance_benefit_periods", ["subscriber_id"])


def downgrade() -> None:
    op.drop_table("insurance_benefit_periods")
    op.drop_column("insurance_subscribers", "benefit_reset_reason")
    op.drop_column("insurance_subscribers", "benefit_period_started")
