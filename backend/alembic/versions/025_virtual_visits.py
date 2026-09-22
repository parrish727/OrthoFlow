"""Wave 5 — persistent virtual visits (replaces in-memory store).

Adds virtual_visits so a doctor-initiated video visit survives backend restarts and exposes a
reliable status lifecycle (waiting → live → ended) to MyOrthoChart. All additive.

Revision ID: 025
Revises: 024
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "virtual_visits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("room_name", sa.String(120), nullable=False),
        sa.Column("staff_token", sa.Text, nullable=False),
        sa.Column("patient_token", sa.Text, nullable=False),
        sa.Column("status", sa.String(12), server_default="waiting", nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("patient_joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_virtual_visits_practice_status", "virtual_visits", ["practice_id", "status"])
    op.create_index("idx_virtual_visits_patient", "virtual_visits", ["patient_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_virtual_visits_patient", table_name="virtual_visits")
    op.drop_index("idx_virtual_visits_practice_status", table_name="virtual_visits")
    op.drop_table("virtual_visits")
