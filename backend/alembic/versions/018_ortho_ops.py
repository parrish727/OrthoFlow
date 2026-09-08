"""Ortho ops: custom CDT, patient comments, chart charges, insurance contracts, payment polls.

Revision ID: 018
Revises: 017
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "custom_cdt_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), server_default="custom"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("short_description", sa.String(255)),
        sa.Column("default_fee", sa.Numeric(10, 2)),
        sa.Column("medicaid_only", sa.Boolean, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_custom_cdt_practice", "custom_cdt_codes", ["practice_id"])
    op.create_index("idx_custom_cdt_code", "custom_cdt_codes", ["practice_id", "code"], unique=True)

    op.create_table(
        "patient_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("chart", sa.String(20), server_default="info"),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_pinned", sa.Boolean, server_default=sa.false()),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("author_name", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_patient_comments_patient_chart", "patient_comments", ["patient_id", "chart"])

    op.create_table(
        "chart_charges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id")),
        sa.Column("cdt_code", sa.String(20), nullable=False),
        sa.Column("description", sa.String(300)),
        sa.Column("fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("tooth_numbers", sa.String(50)),
        sa.Column("is_custom_code", sa.Boolean, server_default=sa.false()),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("collected_at", sa.DateTime(timezone=True)),
        sa.Column("added_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_chart_charges_patient_status", "chart_charges", ["patient_id", "status"])
    op.create_index("idx_chart_charges_practice", "chart_charges", ["practice_id"])

    op.create_table(
        "patient_insurance_contracts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("subscriber_id", UUID(as_uuid=True), sa.ForeignKey("insurance_subscribers.id")),
        sa.Column("tc_proposal_id", UUID(as_uuid=True)),
        sa.Column("total_treatment_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("down_payment", sa.Numeric(12, 2), server_default="0"),
        sa.Column("insurance_estimate", sa.Numeric(12, 2), server_default="0"),
        sa.Column("patient_portion", sa.Numeric(12, 2), server_default="0"),
        sa.Column("estimated_months", sa.Integer),
        sa.Column("payer_kind", sa.String(20), server_default="insurance"),
        sa.Column("billing_cadence", sa.String(20), server_default="monthly"),
        sa.Column("billing_mode", sa.String(10), server_default="auto"),
        sa.Column("claim_destination", sa.String(20), server_default="clearinghouse"),
        sa.Column("initial_claim_sent", sa.Boolean, server_default=sa.false()),
        sa.Column("initial_claim_date", sa.Date),
        sa.Column("next_claim_due", sa.Date),
        sa.Column("daily_payment_poll", sa.Boolean, server_default=sa.true()),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("notes", sa.Text),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_pic_practice_patient", "patient_insurance_contracts", ["practice_id", "patient_id"])
    op.create_index("idx_pic_next_claim_due", "patient_insurance_contracts", ["next_claim_due"])

    op.create_table(
        "claim_payment_polls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("patient_insurance_contracts.id")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("insurance_claims.id")),
        sa.Column("poll_date", sa.Date, server_default=sa.func.current_date()),
        sa.Column("payment_status", sa.String(20), server_default="pending"),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("detail", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_claim_poll_contract", "claim_payment_polls", ["contract_id", "poll_date"])


def downgrade() -> None:
    for t in ["claim_payment_polls", "patient_insurance_contracts", "chart_charges",
              "patient_comments", "custom_cdt_codes"]:
        op.drop_table(t)
