"""Add hygiene_recalls table.

Revision ID: 016
Revises: 015
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hygiene_recalls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("recall_type", sa.String(30), nullable=False),
        sa.Column("interval_months", sa.Integer, nullable=False, server_default="6"),
        sa.Column("last_visit_date", sa.Date, nullable=True),
        sa.Column("next_due_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("auto_schedule", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_recall_practice_status", "hygiene_recalls", ["practice_id", "status"])
    op.create_index("idx_recall_patient", "hygiene_recalls", ["patient_id"])
    op.create_index("idx_recall_practice_next_due", "hygiene_recalls", ["practice_id", "next_due_date"])


def downgrade() -> None:
    op.drop_table("hygiene_recalls")
