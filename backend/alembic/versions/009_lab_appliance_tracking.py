"""Add lab appliance tracking tables.

Revision ID: 009
Revises: 008
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Labs table
    op.create_table(
        "labs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("phone", sa.String(30)),
        sa.Column("email", sa.String(255)),
        sa.Column("address", sa.Text),
        sa.Column("website", sa.String(512)),
        sa.Column("account_number", sa.String(100)),
        sa.Column("avg_turnaround_days", sa.Integer, default=10),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_labs_practice_id", "labs", ["practice_id"])
    op.create_index("idx_labs_practice_active", "labs", ["practice_id", "is_active"])

    # Appliance prescriptions table
    op.create_table(
        "appliance_prescriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("lab_id", UUID(as_uuid=True), sa.ForeignKey("labs.id"), nullable=False),
        sa.Column("prescribed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        # Appliance details
        sa.Column("appliance_type", sa.String(50), nullable=False),
        sa.Column("appliance_name", sa.String(255), nullable=False),
        sa.Column("arch", sa.String(10), nullable=False),
        sa.Column("teeth", sa.String(100)),
        sa.Column("color", sa.String(100)),
        sa.Column("material", sa.String(100)),
        # Notes
        sa.Column("rx_notes", sa.Text),
        sa.Column("special_instructions", sa.Text),
        sa.Column("scan_file_url", sa.String(512)),
        # Status
        sa.Column("status", sa.String(30), default="draft"),
        sa.Column("priority", sa.String(10), default="normal"),
        # Dates
        sa.Column("date_prescribed", sa.Date, nullable=False),
        sa.Column("date_sent_to_lab", sa.Date),
        sa.Column("date_received_by_lab", sa.Date),
        sa.Column("date_shipped", sa.Date),
        sa.Column("date_received", sa.Date),
        sa.Column("date_placed", sa.Date),
        sa.Column("expected_delivery_date", sa.Date),
        # Tracking
        sa.Column("tracking_number", sa.String(100)),
        sa.Column("lab_case_number", sa.String(100)),
        # Remake tracking
        sa.Column("is_remake", sa.Boolean, default=False),
        sa.Column("remake_reason", sa.Text),
        sa.Column("original_prescription_id", UUID(as_uuid=True), sa.ForeignKey("appliance_prescriptions.id")),
        # Cost
        sa.Column("lab_fee", sa.Numeric(10, 2)),
        sa.Column("rush_fee", sa.Numeric(10, 2)),
        # Metadata
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_rx_practice_id", "appliance_prescriptions", ["practice_id"])
    op.create_index("idx_rx_patient_id", "appliance_prescriptions", ["patient_id"])
    op.create_index("idx_rx_lab_id", "appliance_prescriptions", ["lab_id"])
    op.create_index("idx_rx_practice_status", "appliance_prescriptions", ["practice_id", "status"])
    op.create_index("idx_rx_practice_expected", "appliance_prescriptions", ["practice_id", "expected_delivery_date"])

    # Status history (audit trail)
    op.create_table(
        "appliance_status_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("prescription_id", UUID(as_uuid=True), sa.ForeignKey("appliance_prescriptions.id"), nullable=False),
        sa.Column("previous_status", sa.String(30)),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column("changed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_status_history_rx", "appliance_status_history", ["prescription_id", "changed_at"])

    # EasyRx integration settings
    op.create_table(
        "easyrx_integrations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False, unique=True),
        sa.Column("is_enabled", sa.Boolean, default=False),
        sa.Column("easyrx_practice_id", sa.String(100)),
        sa.Column("easyrx_api_key", sa.String(255)),
        sa.Column("launch_url", sa.String(512)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("sync_enabled", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_easyrx_practice", "easyrx_integrations", ["practice_id"], unique=True)


def downgrade() -> None:
    op.drop_table("easyrx_integrations")
    op.drop_table("appliance_status_history")
    op.drop_table("appliance_prescriptions")
    op.drop_table("labs")
