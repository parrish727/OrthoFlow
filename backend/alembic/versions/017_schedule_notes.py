"""Add schedule_notes table (AI + DA daily schedule notes).

Revision ID: 017
Revises: 016
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedule_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("note_date", sa.Date, nullable=False),
        sa.Column("origin", sa.String(20), nullable=False, server_default="da"),
        sa.Column("category", sa.String(20), nullable=False, server_default="operational"),
        sa.Column("placement", sa.String(10), nullable=False, server_default="above"),
        sa.Column("tone", sa.String(10), nullable=False, server_default="info"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source_da_id", UUID(as_uuid=True), sa.ForeignKey("dental_assistants.id"), nullable=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_dismissed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_schedule_notes_practice_date", "schedule_notes", ["practice_id", "note_date"])
    op.create_index("idx_schedule_notes_da", "schedule_notes", ["source_da_id"])


def downgrade() -> None:
    op.drop_index("idx_schedule_notes_da", table_name="schedule_notes")
    op.drop_index("idx_schedule_notes_practice_date", table_name="schedule_notes")
    op.drop_table("schedule_notes")
