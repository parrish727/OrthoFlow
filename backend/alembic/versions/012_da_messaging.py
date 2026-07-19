"""Sprint 3: DA Real-Time Messaging.

Adds: chat_rooms, chat_room_members, chat_messages tables
for practice-scoped real-time messaging with WebSocket support.

Revision ID: 012
Revises: 011
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Chat Rooms ────────────────────────────────────────────────────────────
    op.create_table(
        "chat_rooms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("room_type", sa.String(20), nullable=False, server_default="general"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_chat_rooms_practice_id", "chat_rooms", ["practice_id"])

    # ── Chat Room Members ─────────────────────────────────────────────────────
    op.create_table(
        "chat_room_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("room_id", UUID(as_uuid=True), sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_chat_room_members_room_id", "chat_room_members", ["room_id"])
    op.create_index("idx_chat_room_members_user_id", "chat_room_members", ["user_id"])

    # ── Chat Messages ─────────────────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("room_id", UUID(as_uuid=True), sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("is_edited", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_chat_messages_room_created", "chat_messages", ["room_id", "created_at"])
    op.create_index("idx_chat_messages_sender_id", "chat_messages", ["sender_id"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_room_members")
    op.drop_table("chat_rooms")
