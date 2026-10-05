"""Ceph Suite Phase D — superimposition + progress tracking.

Revision ID: 031
Revises: 030
Create Date: 2026-10-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ceph_superimpositions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("baseline_tracing_id", UUID(as_uuid=True), sa.ForeignKey("ceph_tracings.id"), nullable=False),
        sa.Column("follow_tracing_id", UUID(as_uuid=True), sa.ForeignKey("ceph_tracings.id"), nullable=False),
        sa.Column("method", sa.String(20), server_default="sn", nullable=False),
        sa.Column("unit", sa.String(4), server_default="mm", nullable=False),
        sa.Column("deltas", JSONB, server_default="{}", nullable=False),
        sa.Column("summary", JSONB, server_default="{}", nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ceph_superimp_patient", "ceph_superimpositions", ["practice_id", "patient_id"])


def downgrade() -> None:
    op.drop_index("idx_ceph_superimp_patient", table_name="ceph_superimpositions")
    op.drop_table("ceph_superimpositions")
