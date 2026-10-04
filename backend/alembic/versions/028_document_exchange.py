"""Secure document exchange (office⇄patient): PatientDocument storage/direction columns +
DocumentNotification feed.

Revision ID: 028
Revises: 027
Create Date: 2026-10-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── patient_documents: support real MinIO-backed exchange in both directions ──
    # Make uploaded_by nullable (patient uploads have no staff user) and file_url nullable
    # (new uploads use storage_key + presigned URLs; legacy rows keep file_url).
    op.alter_column("patient_documents", "uploaded_by", existing_type=UUID(as_uuid=True), nullable=True)
    op.alter_column("patient_documents", "file_url", existing_type=sa.String(512), nullable=True)

    op.add_column("patient_documents", sa.Column("storage_key", sa.String(512), nullable=True))
    op.add_column("patient_documents", sa.Column("original_filename", sa.String(255), nullable=True))
    op.add_column("patient_documents", sa.Column("uploaded_by_type", sa.String(10), server_default="staff", nullable=False))
    op.add_column("patient_documents", sa.Column("direction", sa.String(20), server_default="office_to_patient", nullable=False))
    op.add_column("patient_documents", sa.Column("shared_with_patient", sa.Boolean, server_default=sa.true(), nullable=False))
    op.add_column("patient_documents", sa.Column("scan_status", sa.String(20), server_default="clean", nullable=False))
    op.add_column("patient_documents", sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True))

    # ── document_notifications: synced in-app feed for both sides ──
    op.create_table(
        "document_notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("patient_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("audience", sa.String(10), server_default="patient", nullable=False),
        sa.Column("kind", sa.String(30), server_default="document_uploaded", nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("action_url", sa.String(300), nullable=True),
        sa.Column("is_read", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_doc_notif_patient", "document_notifications", ["practice_id", "patient_id", "audience"])
    op.create_index("idx_doc_notif_document", "document_notifications", ["document_id"])


def downgrade() -> None:
    op.drop_index("idx_doc_notif_document", table_name="document_notifications")
    op.drop_index("idx_doc_notif_patient", table_name="document_notifications")
    op.drop_table("document_notifications")

    op.drop_column("patient_documents", "scanned_at")
    op.drop_column("patient_documents", "scan_status")
    op.drop_column("patient_documents", "shared_with_patient")
    op.drop_column("patient_documents", "direction")
    op.drop_column("patient_documents", "uploaded_by_type")
    op.drop_column("patient_documents", "original_filename")
    op.drop_column("patient_documents", "storage_key")

    op.alter_column("patient_documents", "file_url", existing_type=sa.String(512), nullable=False)
    op.alter_column("patient_documents", "uploaded_by", existing_type=UUID(as_uuid=True), nullable=False)
