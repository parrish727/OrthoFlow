"""Add clinical staff roles + team invites table.

Expands UserRole enum: adds doctor, dental_assistant, front_desk.
Adds team_invites table for invite-by-email workflow.

Revision ID: 007
Create Date: 2026-07-09
"""
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    # Expand the role column to accept new values
    # Since the column might be a PG enum or a string depending on how SQLAlchemy created it,
    # safest approach: alter to varchar if it's an enum, or just add values if it's already varchar
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(30)")

    # ── Team Invites ──────────────────────────────────────────────────────────
    op.create_table(
        "team_invites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(100), nullable=False, unique=True),
        sa.Column("status", sa.String(20), server_default="pending"),  # pending, accepted, expired, revoked
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_team_invites_token", "team_invites", ["token"], unique=True)
    op.create_index("idx_team_invites_practice", "team_invites", ["practice_id", "status"])
    op.create_index("idx_team_invites_email", "team_invites", ["email"])


def downgrade() -> None:
    op.drop_table("team_invites")
    # Revert role column would require recreating the enum — skip for simplicity
