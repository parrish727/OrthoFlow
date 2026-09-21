"""Phase 7 — AI letter style profile + treatment-note authorship fields.

Adds doctor_letter_styles (per-doctor few-shot style samples) and author display fields +
updated_at to treatment_notes (DA/doctor initials + color, editable after 24h). All additive.

Revision ID: 023
Revises: 022
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctor_letter_styles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("letter_type", sa.String(40), nullable=False),
        sa.Column("sample_text", sa.Text, nullable=False),
        sa.Column("tone", sa.String(40)),
        sa.Column("use_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_letter_style_user_type", "doctor_letter_styles", ["user_id", "letter_type"])
    op.create_index("idx_letter_style_practice", "doctor_letter_styles", ["practice_id"])

    op.add_column("treatment_notes", sa.Column("author_name", sa.String(200), nullable=True))
    op.add_column("treatment_notes", sa.Column("author_initials", sa.String(10), nullable=True))
    op.add_column("treatment_notes", sa.Column("author_color", sa.String(7), nullable=True))
    op.add_column("treatment_notes", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("treatment_notes", "updated_at")
    op.drop_column("treatment_notes", "author_color")
    op.drop_column("treatment_notes", "author_initials")
    op.drop_column("treatment_notes", "author_name")
    op.drop_table("doctor_letter_styles")
