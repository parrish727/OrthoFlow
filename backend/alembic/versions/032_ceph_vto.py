"""Ceph Suite Phase E — VTO (Visual Treatment Objective) + soft-tissue morph scaffold.

Revision ID: 032
Revises: 031
Create Date: 2026-10-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ceph_vtos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("source_tracing_id", UUID(as_uuid=True), sa.ForeignKey("ceph_tracings.id"), nullable=False),
        sa.Column("params", JSONB, server_default="{}", nullable=False),
        sa.Column("target_landmarks", JSONB, server_default="{}", nullable=False),
        sa.Column("soft_tissue", JSONB, server_default="{}", nullable=False),
        sa.Column("unit", sa.String(4), server_default="mm", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("profile_photo_key", sa.String(512), nullable=True),
        sa.Column("soft_tissue_landmarks", JSONB, nullable=True),
        sa.Column("morph_provider", sa.String(40), nullable=True),
        sa.Column("morph_result_key", sa.String(512), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ceph_vto_patient", "ceph_vtos", ["practice_id", "patient_id"])


def downgrade() -> None:
    op.drop_index("idx_ceph_vto_patient", table_name="ceph_vtos")
    op.drop_table("ceph_vtos")
