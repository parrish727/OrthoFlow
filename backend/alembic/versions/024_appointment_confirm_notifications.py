"""Wave 3 — appointment confirmation fields + appointment notifications feed.

Adds confirmed_at/confirmed_via to appointments (two-way confirm sync across channels /
MyOrthoChart), and an appointment_notifications table powering the patient notification feed
and office-side awareness of portal events (cancellations, confirmations). All additive.

Revision ID: 024
Revises: 023
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("appointments", sa.Column("confirmed_via", sa.String(20), nullable=True))

    op.create_table(
        "appointment_notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("audience", sa.String(10), server_default="patient", nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("action_url", sa.String(300), nullable=True),
        sa.Column("is_read", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_appt_notif_patient", "appointment_notifications", ["practice_id", "patient_id", "audience"])
    op.create_index("idx_appt_notif_appt", "appointment_notifications", ["appointment_id"])


def downgrade() -> None:
    op.drop_index("idx_appt_notif_appt", table_name="appointment_notifications")
    op.drop_index("idx_appt_notif_patient", table_name="appointment_notifications")
    op.drop_table("appointment_notifications")
    op.drop_column("appointments", "confirmed_via")
    op.drop_column("appointments", "confirmed_at")
