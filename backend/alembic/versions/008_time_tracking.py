"""Add time tracking & payroll tables.

Tables: time_entries, pay_rates, payroll_periods
Supports clock in/out, pay rate management, and payroll period tracking.

Revision ID: 008
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    # ── Time Entries ──────────────────────────────────────────────────────────
    op.create_table(
        "time_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("staff_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("clock_in", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clock_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_hours", sa.Numeric(5, 2), nullable=True),
        sa.Column("entry_type", sa.String(20), server_default="regular", nullable=False),  # regular/overtime/pto
        sa.Column("status", sa.String(20), server_default="clocked_in", nullable=False),  # clocked_in/complete/edited/missed
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("edited_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_time_entries_practice_staff", "time_entries", ["practice_id", "staff_id"])
    op.create_index("idx_time_entries_practice_status", "time_entries", ["practice_id", "status"])
    op.create_index("idx_time_entries_staff_clock_in", "time_entries", ["staff_id", "clock_in"])

    # ── Pay Rates ─────────────────────────────────────────────────────────────
    op.create_table(
        "pay_rates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("staff_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(8, 2), nullable=False),
        sa.Column("worker_type", sa.String(20), nullable=False),  # permanent/temporary
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_pay_rates_practice_staff", "pay_rates", ["practice_id", "staff_id"])

    # ── Payroll Periods ───────────────────────────────────────────────────────
    op.create_table(
        "payroll_periods",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),  # open/closed
        sa.Column("total_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("total_pay", sa.Numeric(10, 2), nullable=True),
        sa.Column("closed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_payroll_periods_practice_status", "payroll_periods", ["practice_id", "status"])


def downgrade() -> None:
    op.drop_table("payroll_periods")
    op.drop_table("pay_rates")
    op.drop_table("time_entries")
