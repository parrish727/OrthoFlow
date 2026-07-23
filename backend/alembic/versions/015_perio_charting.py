"""Sprint C: Periodontal Charting.

Adds perio_exams (per-patient exam records) and perio_readings
(per-site 6-point probing measurements). Full 6-point charting:
DB, B, MB, DL, L, ML per tooth (32 teeth × 6 sites = 192 readings).

Revision ID: 015
Revises: 014
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Periodontal exam record (one per exam session)
    op.create_table(
        "perio_exams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("exam_date", sa.Date, nullable=False),
        sa.Column("examiner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_perio_exam_patient", "perio_exams", ["patient_id"])
    op.create_index("idx_perio_exam_practice_date", "perio_exams", ["practice_id", "exam_date"])

    # Individual site readings (up to 192 per exam)
    op.create_table(
        "perio_readings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("exam_id", UUID(as_uuid=True), sa.ForeignKey("perio_exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tooth_number", sa.Integer, nullable=False),
        sa.Column("site", sa.String(20), nullable=False),
        sa.Column("probing_depth", sa.Integer, nullable=False),
        sa.Column("recession", sa.Integer, server_default="0"),
        sa.Column("bleeding_on_probing", sa.Boolean, server_default="false"),
        sa.Column("suppuration", sa.Boolean, server_default="false"),
        sa.Column("plaque", sa.Boolean, server_default="false"),
        sa.Column("furcation_grade", sa.Integer),
        sa.Column("mobility_grade", sa.Integer),
    )
    op.create_index("idx_perio_reading_exam_tooth", "perio_readings", ["exam_id", "tooth_number"])
    op.create_index("idx_perio_reading_patient", "perio_readings", ["exam_id"])


def downgrade() -> None:
    op.drop_table("perio_readings")
    op.drop_table("perio_exams")
