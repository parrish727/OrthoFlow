"""Sprint B: Restorative Tooth Charting.

Adds restorative_charts (per-patient conditions) and tooth_restorations
(individual restoration records per tooth+surface). Coexists with ortho
tooth_charts — separate data layer, same patient.

Revision ID: 014
Revises: 013
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Restorative chart (per-patient, stores tooth conditions as JSON)
    op.create_table(
        "restorative_charts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, unique=True),
        sa.Column("teeth_conditions", JSON, default={}),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("idx_restorative_chart_patient", "restorative_charts", ["patient_id"], unique=True)
    op.create_index("idx_restorative_chart_practice", "restorative_charts", ["practice_id"])

    # Individual tooth restorations (history + treatment plan)
    op.create_table(
        "tooth_restorations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("chart_id", UUID(as_uuid=True), sa.ForeignKey("restorative_charts.id"), nullable=False),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("tooth_number", sa.Integer, nullable=False),
        sa.Column("surfaces", sa.String(10)),
        sa.Column("cdt_code", sa.String(10)),
        sa.Column("restoration_type", sa.String(50), nullable=False),
        sa.Column("material", sa.String(50)),
        sa.Column("status", sa.String(20), default="existing"),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("date_placed", sa.Date),
        sa.Column("date_planned", sa.Date),
        sa.Column("notes", sa.Text),
        sa.Column("lab_case_id", UUID(as_uuid=True), sa.ForeignKey("appliance_prescriptions.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_restoration_patient_tooth", "tooth_restorations", ["patient_id", "tooth_number"])
    op.create_index("idx_restoration_chart", "tooth_restorations", ["chart_id"])
    op.create_index("idx_restoration_status", "tooth_restorations", ["practice_id", "status"])


def downgrade() -> None:
    op.drop_table("tooth_restorations")
    op.drop_table("restorative_charts")
