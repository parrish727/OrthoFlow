"""Sprint A: CDT Code Library + Multi-Specialty Appointment Types.

Adds cdt_codes table (full ADA code set) and appointment_type_templates
(practice-configurable appointment types per specialty).

Revision ID: 013
Revises: 012
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CDT Codes table
    op.create_table(
        "cdt_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("subcategory", sa.String(100)),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("short_description", sa.String(255)),
        sa.Column("specialty", sa.String(30), nullable=False),
        sa.Column("is_common", sa.Boolean, default=False),
        sa.Column("avg_fee", sa.Integer),
        sa.Column("tooth_specific", sa.Boolean, default=True),
        sa.Column("surface_specific", sa.Boolean, default=False),
    )
    op.create_index("idx_cdt_code", "cdt_codes", ["code"], unique=True)
    op.create_index("idx_cdt_category", "cdt_codes", ["category"])
    op.create_index("idx_cdt_specialty", "cdt_codes", ["specialty"])
    op.create_index("idx_cdt_common", "cdt_codes", ["is_common"])

    # Appointment Type Templates
    op.create_table(
        "appointment_type_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("specialty", sa.String(30), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("default_duration_minutes", sa.Integer, default=30),
        sa.Column("default_cdt_codes", sa.Text),
        sa.Column("color", sa.String(7)),
        sa.Column("requires_chair", sa.Boolean, default=True),
        sa.Column("requires_da", sa.Boolean, default=False),
        sa.Column("is_hygiene", sa.Boolean, default=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("sort_order", sa.Integer, default=0),
    )
    op.create_index("idx_appt_type_specialty", "appointment_type_templates", ["specialty"])
    op.create_index("idx_appt_type_active", "appointment_type_templates", ["is_active"])


def downgrade() -> None:
    op.drop_table("appointment_type_templates")
    op.drop_table("cdt_codes")
