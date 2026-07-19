"""Sprint 1: Clinical core enhancements.

Adds: patient SSN (encrypted), dentist field, deactivation support,
patient alerts, family linking, aligner tracking, elastics tracking,
oral hygiene scoring.

Revision ID: 010
Revises: 009
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Patient table enhancements ────────────────────────────────────────────
    op.add_column("patients", sa.Column("ssn_encrypted", sa.String(512), nullable=True))
    op.add_column("patients", sa.Column("general_dentist", sa.String(255), nullable=True))
    op.add_column("patients", sa.Column("general_dentist_phone", sa.String(30), nullable=True))
    op.add_column("patients", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("patients", sa.Column("deactivation_reason", sa.Text, nullable=True))
    op.add_column("patients", sa.Column("oral_hygiene_score", sa.Integer, nullable=True))  # 1-5 stars
    op.add_column("patients", sa.Column("family_id", UUID(as_uuid=True), nullable=True))
    op.add_column("patients", sa.Column("family_relationship", sa.String(50), nullable=True))

    # ── Patient Alerts (allergies, medical conditions, behavioral notes) ──────
    op.create_table(
        "patient_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("alert_type", sa.String(30), nullable=False),  # allergy, medical, behavioral, billing, other
        sa.Column("severity", sa.String(10), nullable=False, server_default="medium"),  # low, medium, high, critical
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_alerts_patient", "patient_alerts", ["patient_id", "is_active"])
    op.create_index("idx_alerts_practice", "patient_alerts", ["practice_id"])

    # ── Patient Families (grouping related patients) ──────────────────────────
    op.create_table(
        "patient_families",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("family_name", sa.String(255), nullable=False),  # e.g. "The Smith Family"
        sa.Column("primary_contact_id", UUID(as_uuid=True), sa.ForeignKey("patients.id")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_families_practice", "patient_families", ["practice_id"])

    # Add FK from patients.family_id → patient_families.id
    op.create_foreign_key("fk_patients_family", "patients", "patient_families", ["family_id"], ["id"])

    # ── Aligner Tracking ──────────────────────────────────────────────────────
    op.create_table(
        "aligner_treatments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("brand", sa.String(100)),  # Invisalign, SureSmile, Spark, In-house, etc.
        sa.Column("total_trays", sa.Integer, nullable=False),
        sa.Column("current_tray", sa.Integer, default=1),
        sa.Column("upper_trays", sa.Integer),  # If upper/lower differ
        sa.Column("lower_trays", sa.Integer),
        sa.Column("wear_hours_per_day", sa.Integer, default=22),
        sa.Column("change_interval_days", sa.Integer, default=14),  # Days per tray
        sa.Column("start_date", sa.Date),
        sa.Column("estimated_end_date", sa.Date),
        sa.Column("refinement_number", sa.Integer, default=0),  # 0 = initial, 1+ = refinement
        sa.Column("notes", sa.Text),
        sa.Column("status", sa.String(20), default="active"),  # active, paused, completed
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_aligner_patient", "aligner_treatments", ["patient_id"])
    op.create_index("idx_aligner_practice", "aligner_treatments", ["practice_id", "status"])

    # Aligner tray change log (tracks actual tray changes for compliance)
    op.create_table(
        "aligner_tray_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("treatment_id", UUID(as_uuid=True), sa.ForeignKey("aligner_treatments.id"), nullable=False),
        sa.Column("tray_number", sa.Integer, nullable=False),
        sa.Column("started_date", sa.Date, nullable=False),
        sa.Column("expected_end_date", sa.Date),
        sa.Column("actual_end_date", sa.Date),  # When patient actually changed
        sa.Column("tracking_status", sa.String(20), default="on_track"),  # on_track, delayed, skipped
        sa.Column("notes", sa.Text),
        sa.Column("logged_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_tray_log_treatment", "aligner_tray_log", ["treatment_id", "tray_number"])

    # ── Elastics Tracking ─────────────────────────────────────────────────────
    op.create_table(
        "elastic_prescriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("elastic_type", sa.String(50), nullable=False),  # Class II, Class III, triangle, box, etc.
        sa.Column("size", sa.String(50)),  # 3/16", 1/4", 5/16", 3/8"
        sa.Column("force", sa.String(50)),  # Light, Medium, Heavy (oz)
        sa.Column("wear_schedule", sa.String(20), nullable=False),  # day, night, full_time (both)
        sa.Column("attachment_from", sa.String(50)),  # e.g. "Upper canine hook"
        sa.Column("attachment_to", sa.String(50)),  # e.g. "Lower molar hook"
        sa.Column("instructions", sa.Text),  # Specific wear instructions
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),  # NULL = ongoing
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("prescribed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_elastics_patient", "elastic_prescriptions", ["patient_id", "is_active"])
    op.create_index("idx_elastics_practice", "elastic_prescriptions", ["practice_id"])


def downgrade() -> None:
    op.drop_table("elastic_prescriptions")
    op.drop_table("aligner_tray_log")
    op.drop_table("aligner_treatments")
    op.drop_constraint("fk_patients_family", "patients", type_="foreignkey")
    op.drop_table("patient_families")
    op.drop_table("patient_alerts")
    op.drop_column("patients", "family_relationship")
    op.drop_column("patients", "family_id")
    op.drop_column("patients", "oral_hygiene_score")
    op.drop_column("patients", "deactivation_reason")
    op.drop_column("patients", "deactivated_at")
    op.drop_column("patients", "general_dentist_phone")
    op.drop_column("patients", "general_dentist")
    op.drop_column("patients", "ssn_encrypted")
