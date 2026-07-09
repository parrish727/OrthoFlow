"""Phase 1: Clinical tables — patients, chairs, DAs, appointments, notes, tooth charts.

Revision ID: 002
Revises: 001
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Integration table (OAuth tokens — replaces NPI column abuse) ──────────
    op.create_table(
        "integrations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("access_token", sa.Text),
        sa.Column("refresh_token", sa.Text),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("realm_id", sa.String(100)),
        sa.Column("config_json", sa.Text),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_integrations_practice_provider", "integrations", ["practice_id", "provider"], unique=True)

    # ── OTP codes table (persistent MFA) ──────────────────────────────────────
    op.create_table(
        "otp_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_otp_user_expires", "otp_codes", ["user_id", "expires_at"])

    # ── Patients ──────────────────────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(20)),
        sa.Column("phone_secondary", sa.String(20)),
        sa.Column("address", sa.Text),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("treatment_phase", sa.String(20), server_default="consultation"),
        sa.Column("referring_doctor", sa.String(255)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_patients_practice_id", "patients", ["practice_id"])
    op.create_index("idx_patients_practice_name", "patients", ["practice_id", "last_name", "first_name"])
    op.create_index("idx_patients_practice_status", "patients", ["practice_id", "status"])

    # ── Chairs ────────────────────────────────────────────────────────────────
    op.create_table(
        "chairs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(7)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("sort_order", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_chairs_practice_id", "chairs", ["practice_id"])

    # ── Dental Assistants ─────────────────────────────────────────────────────
    op.create_table(
        "dental_assistants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_da_practice_id", "dental_assistants", ["practice_id"])

    # ── Appointments ──────────────────────────────────────────────────────────
    op.create_table(
        "appointments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("chair_id", UUID(as_uuid=True), sa.ForeignKey("chairs.id")),
        sa.Column("da_id", UUID(as_uuid=True), sa.ForeignKey("dental_assistants.id")),
        sa.Column("appointment_date", sa.Date, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("duration_minutes", sa.Integer, default=30),
        sa.Column("status", sa.String(20), server_default="scheduled"),
        sa.Column("appointment_type", sa.String(100)),
        sa.Column("procedure_codes", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_appt_practice_date", "appointments", ["practice_id", "appointment_date"])
    op.create_index("idx_appt_patient", "appointments", ["patient_id", "appointment_date"])
    op.create_index("idx_appt_chair_date", "appointments", ["chair_id", "appointment_date"])
    op.create_index("idx_appt_da_date", "appointments", ["da_id", "appointment_date"])
    op.create_index("idx_appt_practice_status", "appointments", ["practice_id", "status"])

    # ── Treatment Notes ───────────────────────────────────────────────────────
    op.create_table(
        "treatment_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id")),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("note_text", sa.Text, nullable=False),
        sa.Column("ai_summary", sa.Text),
        sa.Column("note_type", sa.String(50), server_default="clinical"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_notes_patient", "treatment_notes", ["patient_id", "created_at"])
    op.create_index("idx_notes_appointment", "treatment_notes", ["appointment_id"])

    # ── Tooth Charts ──────────────────────────────────────────────────────────
    op.create_table(
        "tooth_charts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, unique=True),
        sa.Column("teeth_data", JSON, server_default="{}"),
        sa.Column("upper_wire", sa.String(100)),
        sa.Column("lower_wire", sa.String(100)),
        sa.Column("upper_wire_date", sa.Date),
        sa.Column("lower_wire_date", sa.Date),
        sa.Column("appliances", JSON, server_default="[]"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("idx_tooth_chart_patient", "tooth_charts", ["patient_id"], unique=True)

    # ── Add indexes to existing tables (from blocker fixes) ───────────────────
    op.create_index("idx_invoices_practice_status", "invoices", ["practice_id", "status"])
    op.create_index("idx_invoices_practice_created", "invoices", ["practice_id", "created_at"])
    op.create_index("idx_users_practice_id", "users", ["practice_id"])
    op.create_index("idx_audit_practice_timestamp", "audit_logs", ["practice_id", "timestamp"])

    # ── Add columns to existing tables ────────────────────────────────────────
    op.add_column("users", sa.Column("phone", sa.String(20)))
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean, server_default="false"))


def downgrade() -> None:
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "phone")

    op.drop_index("idx_audit_practice_timestamp")
    op.drop_index("idx_users_practice_id")
    op.drop_index("idx_invoices_practice_created")
    op.drop_index("idx_invoices_practice_status")

    op.drop_table("tooth_charts")
    op.drop_table("treatment_notes")
    op.drop_table("appointments")
    op.drop_table("dental_assistants")
    op.drop_table("chairs")
    op.drop_table("patients")
    op.drop_table("otp_codes")
    op.drop_table("integrations")
