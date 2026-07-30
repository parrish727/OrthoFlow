"""
OrthoFlow AI — User Permissions Model
Granular RBAC: role templates + per-user overrides.
Matches topsOrtho/Cloud 9 permission pattern.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Permission Keys ──────────────────────────────────────────────────────────

PERMISSION_CATEGORIES = {
    "schedule": "Schedule",
    "patients": "Patients",
    "clinical": "Clinical",
    "finance": "Finance",
    "communications": "Communications",
    "reports": "Reports",
    "settings": "Settings",
}

PERMISSION_KEYS = {
    # Schedule
    "view_schedule": {"category": "schedule", "label": "View Schedule", "description": "View the daily/weekly schedule"},
    "edit_schedule": {"category": "schedule", "label": "Edit Schedule", "description": "Create, modify, and cancel appointments"},
    # Patients
    "view_patients": {"category": "patients", "label": "View Patients", "description": "View patient list and records"},
    "edit_patients": {"category": "patients", "label": "Edit Patients", "description": "Modify patient demographics and records"},
    "add_patients": {"category": "patients", "label": "Add Patients", "description": "Create new patient records"},
    # Clinical
    "view_clinical_notes": {"category": "clinical", "label": "View Clinical Notes", "description": "View treatment notes and charting"},
    "write_clinical_notes": {"category": "clinical", "label": "Write Clinical Notes", "description": "Create and edit clinical notes"},
    "view_imaging": {"category": "clinical", "label": "View Imaging", "description": "View X-rays and clinical images"},
    "manage_appliances": {"category": "clinical", "label": "Manage Appliances", "description": "Track and manage orthodontic appliances"},
    # Finance
    "view_finance": {"category": "finance", "label": "View Finance", "description": "View ledger, invoices, and balances"},
    "edit_finance": {"category": "finance", "label": "Edit Finance", "description": "Create charges, adjustments, and payments"},
    "process_claims": {"category": "finance", "label": "Process Claims", "description": "Submit and manage insurance claims"},
    "view_insurance": {"category": "finance", "label": "View Insurance", "description": "View insurance plans and eligibility"},
    # Communications
    "view_communications": {"category": "communications", "label": "View Communications", "description": "View message history and templates"},
    "send_messages": {"category": "communications", "label": "Send Messages", "description": "Send SMS/email to patients"},
    "start_virtual_visits": {"category": "communications", "label": "Start Virtual Visits", "description": "Initiate video calls with patients"},
    # Reports
    "view_reports": {"category": "reports", "label": "View Reports", "description": "Access production, collection, and analytics reports"},
    # Settings
    "manage_staff_permissions": {"category": "settings", "label": "Manage Staff Permissions", "description": "Configure permissions for other staff members"},
    "manage_practice_settings": {"category": "settings", "label": "Manage Practice Settings", "description": "Edit practice info, branding, and integrations"},
}

# ── Role Templates ────────────────────────────────────────────────────────────

ROLE_TEMPLATES: dict[str, list[str]] = {
    "owner": list(PERMISSION_KEYS.keys()),  # All permissions
    "doctor": list(PERMISSION_KEYS.keys()),  # All permissions
    "office_manager": [
        "view_schedule", "edit_schedule",
        "view_patients", "edit_patients", "add_patients",
        "view_clinical_notes",
        "view_finance", "edit_finance", "process_claims", "view_insurance",
        "view_communications", "send_messages", "start_virtual_visits",
        "view_reports",
        "manage_staff_permissions", "manage_practice_settings",
    ],
    "dental_assistant": [
        "view_schedule",
        "view_patients",
        "view_clinical_notes", "write_clinical_notes", "view_imaging", "manage_appliances",
        "view_communications",
        "start_virtual_visits",
    ],
    "front_desk": [
        "view_schedule", "edit_schedule",
        "view_patients", "edit_patients", "add_patients",
        "view_finance", "edit_finance", "view_insurance",
        "view_communications", "send_messages",
    ],
}


# ── Model ─────────────────────────────────────────────────────────────────────

class UserPermission(Base):
    """Per-user permission grants. Overrides role template defaults."""
    __tablename__ = "user_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    permission_key: Mapped[str] = mapped_column(String(100), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (
        Index("idx_user_permissions_user", "user_id"),
        Index("idx_user_permissions_practice", "practice_id"),
        Index("idx_user_permissions_user_key", "user_id", "permission_key", unique=True),
    )
