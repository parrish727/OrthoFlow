"""Initial schema

Revision ID: 001
Revises: None
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('practices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('npi', sa.String(20)),
        sa.Column('address', sa.Text),
        sa.Column('tier', sa.String(20), server_default='standard'),
        sa.Column('logo_url', sa.String(512)),
        sa.Column('primary_color', sa.String(7)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table('users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('practice_id', UUID(as_uuid=True), sa.ForeignKey('practices.id'), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), server_default='bookkeeper'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table('invoices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('practice_id', UUID(as_uuid=True), sa.ForeignKey('practices.id'), nullable=False),
        sa.Column('vendor_name', sa.String(255), nullable=False),
        sa.Column('invoice_number', sa.String(100)),
        sa.Column('invoice_date', sa.DateTime),
        sa.Column('due_date', sa.DateTime),
        sa.Column('total_amount', sa.Float, server_default='0'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('s3_key', sa.String(512)),
        sa.Column('raw_text', sa.Text),
        sa.Column('coded_json', sa.Text),
        sa.Column('confidence_score', sa.Float),
        sa.Column('approved_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('approved_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table('line_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('invoice_id', UUID(as_uuid=True), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('quantity', sa.Float),
        sa.Column('unit_price', sa.Float),
        sa.Column('total', sa.Float, server_default='0'),
        sa.Column('category', sa.String(100)),
        sa.Column('gl_code', sa.String(50)),
        sa.Column('confidence', sa.Float),
    )

    op.create_table('audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('practice_id', UUID(as_uuid=True), sa.ForeignKey('practices.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(100)),
        sa.Column('details', sa.Text),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('line_items')
    op.drop_table('invoices')
    op.drop_table('users')
    op.drop_table('practices')
