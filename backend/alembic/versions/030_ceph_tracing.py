"""Ceph Suite Phase A — cephalometric tracing + analysis definitions.

Revision ID: 030
Revises: 029
Create Date: 2026-10-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ceph_tracings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("image_id", UUID(as_uuid=True), sa.ForeignKey("patient_images.id"), nullable=False),
        sa.Column("analysis_type", sa.String(40), server_default="abo", nullable=False),
        sa.Column("landmarks", JSONB, server_default="{}", nullable=False),
        sa.Column("measurements", JSONB, server_default="{}", nullable=False),
        sa.Column("calibration", JSONB, nullable=True),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("is_ai_assisted", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("ai_confidence", sa.Float, nullable=True),
        sa.Column("traced_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("finalized_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ceph_tracing_patient", "ceph_tracings", ["practice_id", "patient_id"])
    op.create_index("idx_ceph_tracing_image", "ceph_tracings", ["image_id"])

    op.create_table(
        "ceph_analysis_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=True),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_builtin", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("landmark_keys", JSONB, server_default="[]", nullable=False),
        sa.Column("measurement_keys", JSONB, server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ceph_analysis_practice", "ceph_analysis_definitions", ["practice_id", "key"])


def downgrade() -> None:
    op.drop_index("idx_ceph_analysis_practice", table_name="ceph_analysis_definitions")
    op.drop_table("ceph_analysis_definitions")
    op.drop_index("idx_ceph_tracing_image", table_name="ceph_tracings")
    op.drop_index("idx_ceph_tracing_patient", table_name="ceph_tracings")
    op.drop_table("ceph_tracings")
