"""Patient Portal + Reporting + Migration tables.

Adds: portal_accounts, portal_forms, portal_form_submissions, portal_messages,
      report_snapshots, migration_jobs, migration_records.

Revision ID: 006
Create Date: 2026-07-09
"""
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade() -> None:
    # ── Portal Accounts (patient login, separate from staff users) ─────────────
    op.create_table(
        "portal_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("verification_token", sa.String(100)),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_portal_accounts_email", "portal_accounts", ["practice_id", "email"], unique=True)
    op.create_index("idx_portal_accounts_patient", "portal_accounts", ["patient_id"], unique=True)

    # ── Portal Forms (intake forms, consent forms, health history) ─────────────
    op.create_table(
        "portal_forms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("form_type", sa.String(30), nullable=False),  # intake, consent, health_history, financial, custom
        sa.Column("description", sa.String(500)),
        sa.Column("fields", JSONB, nullable=False),  # [{id, label, type, required, options}]
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_required_new_patient", sa.Boolean, server_default="false"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_portal_forms_practice", "portal_forms", ["practice_id", "form_type"])

    # ── Portal Form Submissions ───────────────────────────────────────────────
    op.create_table(
        "portal_form_submissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("form_id", UUID(as_uuid=True), sa.ForeignKey("portal_forms.id"), nullable=False),
        sa.Column("responses", JSONB, nullable=False),  # {field_id: value}
        sa.Column("status", sa.String(20), server_default="submitted"),  # submitted, reviewed, archived
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_form_submissions_patient", "portal_form_submissions", ["patient_id"])
    op.create_index("idx_form_submissions_practice", "portal_form_submissions", ["practice_id", "status"])

    # ── Portal Messages (patient ↔ office messaging) ──────────────────────────
    op.create_table(
        "portal_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),  # inbound (patient→office), outbound (office→patient)
        sa.Column("subject", sa.String(200)),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("sent_by_staff", UUID(as_uuid=True), sa.ForeignKey("users.id")),  # null if from patient
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_portal_messages_patient", "portal_messages", ["patient_id", "created_at"])
    op.create_index("idx_portal_messages_unread", "portal_messages", ["practice_id", "direction", "is_read"])

    # ── Report Snapshots (cached monthly reports) ─────────────────────────────
    op.create_table(
        "report_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False),  # production, collections, ar_aging, provider_productivity
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("generated_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("idx_report_snapshots_practice", "report_snapshots", ["practice_id", "report_type", "period_start"])

    # ── Migration Jobs (patient data import tracking) ─────────────────────────
    op.create_table(
        "migration_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("practice_id", UUID(as_uuid=True), sa.ForeignKey("practices.id"), nullable=False),
        sa.Column("source_system", sa.String(50), nullable=False),  # dolphin, ortho2, eaglesoft, csv
        sa.Column("status", sa.String(20), server_default="pending"),  # pending, mapping, validating, importing, complete, failed
        sa.Column("total_records", sa.Integer, server_default="0"),
        sa.Column("imported_records", sa.Integer, server_default="0"),
        sa.Column("failed_records", sa.Integer, server_default="0"),
        sa.Column("skipped_records", sa.Integer, server_default="0"),
        sa.Column("field_mapping", JSONB),  # {source_field: target_field}
        sa.Column("validation_errors", JSONB),  # [{row, field, error}]
        sa.Column("import_log", sa.Text),
        sa.Column("source_file_path", sa.String(500)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_migration_jobs_practice", "migration_jobs", ["practice_id", "status"])


def downgrade() -> None:
    op.drop_table("migration_jobs")
    op.drop_table("report_snapshots")
    op.drop_table("portal_messages")
    op.drop_table("portal_form_submissions")
    op.drop_table("portal_forms")
    op.drop_table("portal_accounts")
