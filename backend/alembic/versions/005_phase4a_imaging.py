"""Phase 4a — Imaging Suite tables.

Adds: patient_images, imaging_series, imaging_alerts.
Foundation for web upload + cloud storage + OHIF viewer.
Architected for Phase 4b edge appliance DICOM ingest.

Revision ID: 005
Create Date: 2026-07-09
"""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade() -> None:
    # ── Imaging Series (groups related images, e.g. full-mouth series) ─────────
    op.create_table(
        "imaging_series",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id")),
        sa.Column("series_type", sa.String(30), nullable=False),  # full_mouth, progress, initial_records, final_records, custom
        sa.Column("description", sa.String(300)),
        sa.Column("image_count", sa.Integer, server_default="0"),
        sa.Column("captured_date", sa.Date, nullable=False),
        sa.Column("captured_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_series_practice_patient", "imaging_series", ["practice_id", "patient_id"])
    op.create_index("idx_series_date", "imaging_series", ["patient_id", "captured_date"])

    # ── Patient Images ────────────────────────────────────────────────────────
    op.create_table(
        "patient_images",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("series_id", UUID(as_uuid=True), sa.ForeignKey("imaging_series.id")),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id")),
        # Image classification
        sa.Column("image_type", sa.String(30), nullable=False),  # pano, ceph, pa, intraoral_photo, cbct, other
        sa.Column("modality", sa.String(20)),  # CR (computed radiography), DX (digital xray), CT (CBCT), XC (photo)
        sa.Column("description", sa.String(300)),
        sa.Column("tooth_numbers", sa.String(50)),  # relevant teeth (for PAs)
        # Storage
        sa.Column("storage_path", sa.String(500), nullable=False),  # MinIO object key: practice_id/patient_id/date/filename
        sa.Column("storage_bucket", sa.String(100), nullable=False, server_default="orthoflow-imaging"),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("content_type", sa.String(100)),  # application/dicom, image/png, image/jpeg
        sa.Column("checksum_sha256", sa.String(64)),  # integrity verification
        # DICOM metadata (populated when source is DICOM)
        sa.Column("dicom_study_uid", sa.String(128)),
        sa.Column("dicom_series_uid", sa.String(128)),
        sa.Column("dicom_instance_uid", sa.String(128)),
        sa.Column("dicom_metadata", JSONB),  # parsed DICOM tags (non-PHI subset)
        # Source tracking (for 4b edge appliance integration)
        sa.Column("source", sa.String(20), nullable=False, server_default="upload"),  # upload, edge_appliance, dicom_push, import
        sa.Column("source_device_id", sa.String(100)),  # AE Title or device serial for 4b
        sa.Column("source_device_name", sa.String(200)),  # "Planmeca ProMax 3D" etc.
        # Status
        sa.Column("status", sa.String(20), server_default="active"),  # active, archived, deleted
        sa.Column("captured_date", sa.Date, nullable=False),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_images_practice_patient", "patient_images", ["practice_id", "patient_id"])
    op.create_index("idx_images_patient_type", "patient_images", ["patient_id", "image_type"])
    op.create_index("idx_images_patient_date", "patient_images", ["patient_id", "captured_date"])
    op.create_index("idx_images_series", "patient_images", ["series_id"])
    op.create_index("idx_images_dicom_study", "patient_images", ["dicom_study_uid"])
    op.create_index("idx_images_source_device", "patient_images", ["source_device_id"])

    # ── Imaging Alerts (overdue tracking) ─────────────────────────────────────
    op.create_table(
        "imaging_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("image_type", sa.String(30), nullable=False),  # which type is overdue
        sa.Column("last_taken_date", sa.Date),  # when was the last one taken
        sa.Column("due_date", sa.Date, nullable=False),  # when the next one is due
        sa.Column("status", sa.String(20), server_default="pending"),  # pending, dismissed, completed
        sa.Column("treatment_phase", sa.String(20)),  # what phase triggered this alert
        sa.Column("rule_description", sa.String(200)),  # e.g. "Progress pano every 6 months during active treatment"
        sa.Column("dismissed_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("dismissed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_image_id", UUID(as_uuid=True), sa.ForeignKey("patient_images.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_alerts_practice_status", "imaging_alerts", ["practice_id", "status"])
    op.create_index("idx_alerts_patient", "imaging_alerts", ["patient_id"])
    op.create_index("idx_alerts_due_date", "imaging_alerts", ["due_date", "status"])


def downgrade() -> None:
    op.drop_table("imaging_alerts")
    op.drop_table("patient_images")
    op.drop_table("imaging_series")
