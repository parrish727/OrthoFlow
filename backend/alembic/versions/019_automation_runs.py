"""Automation runs audit table.

Revision ID: 019
Revises: 018
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("run_date", sa.Date, server_default=sa.func.current_date()),
        sa.Column("task", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), server_default="completed"),
        sa.Column("items_processed", sa.Integer, server_default="0"),
        sa.Column("summary", sa.Text),
        sa.Column("detail", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_automation_practice_date", "automation_runs", ["practice_id", "run_date"])
    op.create_index("idx_automation_task_date", "automation_runs", ["practice_id", "task", "run_date"], unique=True)


def downgrade() -> None:
    op.drop_table("automation_runs")
