"""Phase 3 — Patient Communications tables.

Adds: communication_preferences, message_templates, message_log, scheduled_messages.
Supports automated reminders, two-way texting, TCPA compliance.

Revision ID: 004
Create Date: 2026-07-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade() -> None:
    # ── Communication Preferences (per patient) ───────────────────────────────
    op.create_table(
        "communication_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, unique=True),
        # Channel preferences
        sa.Column("sms_enabled", sa.Boolean, server_default="true"),
        sa.Column("email_enabled", sa.Boolean, server_default="true"),
        sa.Column("preferred_channel", sa.String(10), server_default="sms"),  # sms, email, both
        sa.Column("phone_number", sa.String(20)),  # verified SMS number
        sa.Column("email_address", sa.String(255)),  # verified email
        # Reminder preferences
        sa.Column("reminder_24hr", sa.Boolean, server_default="true"),
        sa.Column("reminder_2hr", sa.Boolean, server_default="true"),
        sa.Column("recall_reminders", sa.Boolean, server_default="true"),
        sa.Column("birthday_messages", sa.Boolean, server_default="false"),
        # Quiet hours (don't send during these times)
        sa.Column("quiet_start", sa.Time),  # e.g. 21:00
        sa.Column("quiet_end", sa.Time),  # e.g. 08:00
        # TCPA compliance
        sa.Column("tcpa_consent", sa.Boolean, server_default="false"),
        sa.Column("tcpa_consent_date", sa.DateTime(timezone=True)),
        sa.Column("tcpa_consent_method", sa.String(50)),  # written, verbal, electronic, sms_keyword
        sa.Column("tcpa_opt_out_date", sa.DateTime(timezone=True)),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_comm_prefs_practice_patient", "communication_preferences", ["practice_id", "patient_id"], unique=True)

    # ── Message Templates ─────────────────────────────────────────────────────
    op.create_table(
        "message_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("template_type", sa.String(30), nullable=False),  # appointment_reminder, recall, birthday, custom, confirmation_request
        sa.Column("channel", sa.String(10), nullable=False, server_default="sms"),  # sms, email, both
        sa.Column("subject", sa.String(200)),  # email subject only
        sa.Column("body", sa.Text, nullable=False),  # supports {variables}
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_default", sa.Boolean, server_default="false"),
        sa.Column("send_timing", sa.String(20)),  # 24hr_before, 2hr_before, day_of, custom
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_msg_templates_practice", "message_templates", ["practice_id", "template_type"])

    # ── Message Log (all sent + received) ─────────────────────────────────────
    op.create_table(
        "message_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id")),
        sa.Column("direction", sa.String(10), nullable=False),  # outbound, inbound
        sa.Column("channel", sa.String(10), nullable=False),  # sms, email
        sa.Column("to_address", sa.String(255), nullable=False),  # phone or email
        sa.Column("from_address", sa.String(255)),
        sa.Column("subject", sa.String(200)),  # email only
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("message_templates.id")),
        # Delivery tracking
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),  # queued, sent, delivered, failed, replied
        sa.Column("external_id", sa.String(100)),  # Twilio SID or email message ID
        sa.Column("error_message", sa.String(500)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("replied_at", sa.DateTime(timezone=True)),
        sa.Column("reply_body", sa.Text),
        # Metadata
        sa.Column("metadata", JSONB),  # extra data (campaign, batch_id, etc.)
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_msg_log_practice_patient", "message_log", ["practice_id", "patient_id"])
    op.create_index("idx_msg_log_status", "message_log", ["practice_id", "status"])
    op.create_index("idx_msg_log_appointment", "message_log", ["appointment_id"])
    op.create_index("idx_msg_log_created", "message_log", ["practice_id", "created_at"])
    op.create_index("idx_msg_log_external_id", "message_log", ["external_id"])

    # ── Scheduled Messages (queue for future sending) ─────────────────────────
    op.create_table(
        "scheduled_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_id", UUID(as_uuid=True), sa.ForeignKey("appointments.id")),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("message_templates.id")),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("to_address", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(200)),
        sa.Column("body", sa.Text, nullable=False),  # rendered template (variables resolved)
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),  # pending, sent, cancelled, failed
        sa.Column("attempts", sa.Integer, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.String(500)),
        sa.Column("cancelled_reason", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_scheduled_msg_due", "scheduled_messages", ["scheduled_for", "status"])
    op.create_index("idx_scheduled_msg_appointment", "scheduled_messages", ["appointment_id"])
    op.create_index("idx_scheduled_msg_patient", "scheduled_messages", ["patient_id"])


def downgrade() -> None:
    op.drop_table("scheduled_messages")
    op.drop_table("message_log")
    op.drop_table("message_templates")
    op.drop_table("communication_preferences")
