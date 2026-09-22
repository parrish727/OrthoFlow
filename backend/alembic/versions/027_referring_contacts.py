"""Wave 5 — referring-doctor contact list (for referral / thank-you letters + email relay).

Revision ID: 027
Revises: 026
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referring_contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("practice_name", sa.String(200), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("specialty", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_referring_contacts_practice", "referring_contacts", ["practice_id", "is_active"])


def downgrade() -> None:
    op.drop_index("idx_referring_contacts_practice", table_name="referring_contacts")
    op.drop_table("referring_contacts")
