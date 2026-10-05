"""Ceph Suite Phase F — 3D CBCT scans (DICOM ingest + 3D landmarks + Opus interpretation).

Revision ID: 033
Revises: 032
Create Date: 2026-10-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ceph_cbct_scans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("image_id", UUID(as_uuid=True), sa.ForeignKey("patient_images.id"), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("source_software", sa.String(60), nullable=True),
        sa.Column("dicom_study_uid", sa.String(128), nullable=True),
        sa.Column("dicom_series_uid", sa.String(128), nullable=True),
        sa.Column("dicom_metadata", JSONB, nullable=True),
        sa.Column("voxel_spacing_mm", JSONB, nullable=True),
        sa.Column("landmarks_3d", JSONB, server_default="{}", nullable=False),
        sa.Column("measurements_3d", JSONB, server_default="{}", nullable=False),
        sa.Column("interpretation", sa.Text, nullable=True),
        sa.Column("geometry_provider", sa.String(40), nullable=True),
        sa.Column("status", sa.String(20), server_default="uploaded", nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ceph_cbct_patient", "ceph_cbct_scans", ["practice_id", "patient_id"])
    op.create_index("idx_ceph_cbct_study", "ceph_cbct_scans", ["dicom_study_uid"])


def downgrade() -> None:
    op.drop_index("idx_ceph_cbct_study", table_name="ceph_cbct_scans")
    op.drop_index("idx_ceph_cbct_patient", table_name="ceph_cbct_scans")
    op.drop_table("ceph_cbct_scans")
