"""Sprint 2: Workflow features.

Adds: patient visit status tracking, recent patient searches,
patient documents, imaging_category column on imaging_series.

Revision ID: 011
Revises: 010
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Patient Visit Status (chair-side tracker) ─────────────────────────────
    op.create_table(
        "patient_visit_status",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("chair_id", UUID(as_uuid=True), sa.ForeignKey("chairs.id"), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(timezone=True)),
        sa.Column("seated_at", sa.DateTime(timezone=True)),
        sa.Column("checked_out_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_visit_status_practice_status", "patient_visit_status", ["practice_id", "status"])
    op.create_index("idx_visit_status_appointment", "patient_visit_status", ["appointment_id"])

    # ── Recent Patient Searches ───────────────────────────────────────────────
    op.create_table(
        "recent_patient_searches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("searched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_recent_searches_user_time",
        "recent_patient_searches",
        ["user_id", sa.text("searched_at DESC")],
    )
    op.create_unique_constraint(
        "uq_recent_searches_user_patient",
        "recent_patient_searches",
        ["user_id", "patient_id"],
    )

    # ── Patient Documents ─────────────────────────────────────────────────────
    op.create_table(
        "patient_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(512), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_documents_patient", "patient_documents", ["patient_id"])

    # ── Imaging Series: add imaging_category column ───────────────────────────
    op.add_column(
        "imaging_series",
        sa.Column("imaging_category", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("imaging_series", "imaging_category")
    op.drop_table("patient_documents")
    op.drop_table("recent_patient_searches")
    op.drop_table("patient_visit_status")
