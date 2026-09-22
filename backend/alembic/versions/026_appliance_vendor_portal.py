"""Wave 5 — appliance vendor portal fields + per-office aligner company.

Adds appliance_prescriptions.vendor_token (lab uses it to update order status via the vendor
portal) and labs.is_aligner_company + labs.aligner_brand (per-office aligner vendor choice).
All additive.

Revision ID: 026
Revises: 025
Create Date: 2026-09-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("appliance_prescriptions", sa.Column("vendor_token", sa.String(64), nullable=True))
    op.add_column("labs", sa.Column("is_aligner_company", sa.Boolean, server_default=sa.false(), nullable=False))
    op.add_column("labs", sa.Column("aligner_brand", sa.String(100), nullable=True))
    op.create_index("idx_appliance_rx_vendor_token", "appliance_prescriptions", ["vendor_token"])
    # Vendor-portal status updates have no staff user → allow null.
    op.alter_column("appliance_status_history", "changed_by", existing_type=UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    op.alter_column("appliance_status_history", "changed_by", existing_type=UUID(as_uuid=True), nullable=False)
    op.drop_index("idx_appliance_rx_vendor_token", table_name="appliance_prescriptions")
    op.drop_column("labs", "aligner_brand")
    op.drop_column("labs", "is_aligner_company")
    op.drop_column("appliance_prescriptions", "vendor_token")
