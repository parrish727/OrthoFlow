"""Phase 2 — Finance & Insurance tables.

Adds: insurance_subscribers, patient_ledger_entries, payment_postings, claim_line_items.
Extends: insurance_claims with additional fields for full lifecycle.

Revision ID: 003
Create Date: 2026-07-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade() -> None:
    # ── Insurance Subscribers (links patient to insurance plan) ────────────────
    op.create_table(
        "insurance_subscribers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("relationship", sa.String(20), nullable=False, server_default="self"),  # self, spouse, child, other
        sa.Column("subscriber_id", sa.String(50), nullable=False),  # insurance member ID
        sa.Column("group_number", sa.String(50)),
        sa.Column("payer_id", sa.String(50), nullable=False),
        sa.Column("payer_name", sa.String(200), nullable=False),
        sa.Column("plan_name", sa.String(200)),
        sa.Column("plan_type", sa.String(20), server_default="commercial"),  # commercial, medicare, medicaid, tricare
        sa.Column("coverage_type", sa.String(20), server_default="primary"),  # primary, secondary, tertiary
        sa.Column("subscriber_first_name", sa.String(100)),
        sa.Column("subscriber_last_name", sa.String(100)),
        sa.Column("subscriber_dob", sa.Date),
        sa.Column("effective_date", sa.Date),
        sa.Column("termination_date", sa.Date),
        sa.Column("copay_amount", sa.Numeric(10, 2)),
        sa.Column("deductible_amount", sa.Numeric(10, 2)),
        sa.Column("deductible_met", sa.Numeric(10, 2), server_default="0"),
        sa.Column("annual_max", sa.Numeric(10, 2)),
        sa.Column("annual_used", sa.Numeric(10, 2), server_default="0"),
        sa.Column("ortho_lifetime_max", sa.Numeric(10, 2)),
        sa.Column("ortho_lifetime_used", sa.Numeric(10, 2), server_default="0"),
        sa.Column("ortho_coverage_pct", sa.Integer),  # e.g. 50 = 50%
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_eligibility_check", sa.DateTime(timezone=True)),
        sa.Column("eligibility_status", sa.String(20)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ins_sub_practice_patient", "insurance_subscribers", ["practice_id", "patient_id"])
    op.create_index("idx_ins_sub_subscriber_id", "insurance_subscribers", ["subscriber_id"])

    # ── Patient Ledger Entries (charges, payments, adjustments) ────────────────
    op.create_table(
        "patient_ledger_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("entry_type", sa.String(20), nullable=False),  # charge, payment, adjustment, credit, refund
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),  # positive for charges, negative for payments/credits
        sa.Column("running_balance", sa.Numeric(12, 2)),  # computed on insert
        sa.Column("cdt_code", sa.String(10)),  # if this is a procedure charge
        sa.Column("tooth_numbers", sa.String(50)),  # e.g. "8,9,10"
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("insurance_claims.id")),  # linked claim
        sa.Column("payment_posting_id", UUID(as_uuid=True)),  # linked payment posting
        sa.Column("provider_id", UUID(as_uuid=True)),  # who performed the service
        sa.Column("service_date", sa.Date),
        sa.Column("posted_date", sa.Date, nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("payment_method", sa.String(20)),  # cash, check, card, insurance, adjustment
        sa.Column("reference_number", sa.String(50)),  # check number, transaction ID, etc.
        sa.Column("notes", sa.Text),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ledger_practice_patient", "patient_ledger_entries", ["practice_id", "patient_id"])
    op.create_index("idx_ledger_patient_date", "patient_ledger_entries", ["patient_id", "posted_date"])
    op.create_index("idx_ledger_claim", "patient_ledger_entries", ["claim_id"])
    op.create_index("idx_ledger_entry_type", "patient_ledger_entries", ["practice_id", "entry_type"])

    # ── Claim Line Items (individual procedures on a claim) ───────────────────
    op.create_table(
        "claim_line_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("insurance_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_number", sa.Integer, nullable=False),
        sa.Column("cdt_code", sa.String(10), nullable=False),
        sa.Column("description", sa.String(300)),
        sa.Column("tooth_numbers", sa.String(50)),
        sa.Column("surface", sa.String(10)),  # M, D, B, L, O combinations
        sa.Column("quantity", sa.Integer, server_default="1"),
        sa.Column("billed_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("allowed_amount", sa.Numeric(12, 2)),
        sa.Column("paid_amount", sa.Numeric(12, 2)),
        sa.Column("adjustment_amount", sa.Numeric(12, 2)),
        sa.Column("patient_responsibility", sa.Numeric(12, 2)),
        sa.Column("denial_code", sa.String(20)),
        sa.Column("denial_reason", sa.String(300)),
        sa.Column("service_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_claim_lines_claim", "claim_line_items", ["claim_id"])

    # ── Payment Postings (ERA/835 batch payments) ─────────────────────────────
    op.create_table(
        "payment_postings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),  # era, manual, patient
        sa.Column("payer_name", sa.String(200)),
        sa.Column("check_number", sa.String(50)),
        sa.Column("check_date", sa.Date),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("applied_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("unapplied_amount", sa.Numeric(12, 2)),
        sa.Column("era_trace_number", sa.String(50)),  # 835 trace
        sa.Column("era_data", JSONB),  # raw ERA/835 parsed data
        sa.Column("status", sa.String(20), server_default="pending"),  # pending, partial, complete
        sa.Column("posted_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("posted_date", sa.Date, server_default=sa.text("CURRENT_DATE")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_payment_posting_practice", "payment_postings", ["practice_id"])
    op.create_index("idx_payment_posting_status", "payment_postings", ["practice_id", "status"])
    op.create_index("idx_payment_posting_era", "payment_postings", ["era_trace_number"])

    # ── Add appeal fields to insurance_claims ─────────────────────────────────
    op.add_column("insurance_claims", sa.Column("appeal_text", sa.Text))
    op.add_column("insurance_claims", sa.Column("appeal_date", sa.DateTime(timezone=True)))
    op.add_column("insurance_claims", sa.Column("appeal_status", sa.String(20)))
    op.add_column("insurance_claims", sa.Column("original_denial_eob", sa.Text))


def downgrade() -> None:
    op.drop_column("insurance_claims", "original_denial_eob")
    op.drop_column("insurance_claims", "appeal_status")
    op.drop_column("insurance_claims", "appeal_date")
    op.drop_column("insurance_claims", "appeal_text")
    op.drop_table("payment_postings")
    op.drop_table("claim_line_items")
    op.drop_table("patient_ledger_entries")
    op.drop_table("insurance_subscribers")
