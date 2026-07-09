"""OrthoFlow API — Message Template CRUD.

Manages reusable message templates with variable substitution for
appointment reminders, recall notices, and custom communications.
Supported variables: {patient_name}, {appointment_date}, {appointment_time},
{provider_name}, {office_name}, {office_phone}
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.communications import MessageTemplate

router = APIRouter(prefix="/api/v1/communications/templates", tags=["communication-templates"])


# ── Constants ─────────────────────────────────────────────────────────────────

SUPPORTED_VARIABLES = [
    "{patient_name}",
    "{appointment_date}",
    "{appointment_time}",
    "{provider_name}",
    "{office_name}",
    "{office_phone}",
]

SAMPLE_VARIABLES = {
    "{patient_name}": "Jane Smith",
    "{appointment_date}": "Monday, July 14",
    "{appointment_time}": "2:30 PM",
    "{provider_name}": "Dr. Johnson",
    "{office_name}": "Bright Smiles Orthodontics",
    "{office_phone}": "(555) 123-4567",
}

TEMPLATE_TYPES = ["appointment_reminder", "recall", "birthday", "custom", "confirmation", "cancellation"]


# ── Schemas ───────────────────────────────────────────────────────────────────

class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    template_type: str = Field(..., min_length=1, max_length=30)
    channel: str = Field("sms", pattern="^(sms|email)$")
    subject: str | None = Field(None, max_length=200)
    body: str = Field(..., min_length=1, max_length=1600)
    is_default: bool = False
    send_timing: str | None = Field(None, max_length=20)


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    template_type: str | None = Field(None, min_length=1, max_length=30)
    channel: str | None = Field(None, pattern="^(sms|email)$")
    subject: str | None = Field(None, max_length=200)
    body: str | None = Field(None, min_length=1, max_length=1600)
    is_default: bool | None = None
    send_timing: str | None = Field(None, max_length=20)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _template_to_dict(tmpl: MessageTemplate) -> dict:
    return {
        "id": str(tmpl.id),
        "name": tmpl.name,
        "template_type": tmpl.template_type,
        "channel": tmpl.channel,
        "subject": tmpl.subject,
        "body": tmpl.body,
        "is_active": tmpl.is_active,
        "is_default": tmpl.is_default,
        "send_timing": tmpl.send_timing,
        "supported_variables": SUPPORTED_VARIABLES,
        "created_at": tmpl.created_at.isoformat(),
        "updated_at": tmpl.updated_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
async def list_templates(
    template_type: str | None = None,
    channel: str | None = None,
    active_only: bool = True,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """List all message templates for the practice, optionally filtered by type."""
    practice_id = user["practice_id"]
    q = select(MessageTemplate).where(MessageTemplate.practice_id == practice_id)

    if template_type:
        q = q.where(MessageTemplate.template_type == template_type)
    if channel:
        q = q.where(MessageTemplate.channel == channel)
    if active_only:
        q = q.where(MessageTemplate.is_active.is_(True))

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(MessageTemplate.template_type, MessageTemplate.name)
    q = q.offset((page - 1) * size).limit(size)
    result = await db.execute(q)
    templates = result.scalars().all()

    return {
        "templates": [_template_to_dict(t) for t in templates],
        "total": total,
        "page": page,
        "size": size,
        "supported_variables": SUPPORTED_VARIABLES,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Create a new message template."""
    practice_id = user["practice_id"]

    tmpl = MessageTemplate(
        practice_id=practice_id,
        name=body.name,
        template_type=body.template_type,
        channel=body.channel,
        subject=body.subject,
        body=body.body,
        is_default=body.is_default,
        send_timing=body.send_timing,
    )
    db.add(tmpl)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="message_template.create",
        resource_type="message_template",
        resource_id=None,
        details=f"Created template: {body.name} ({body.template_type})",
    )
    await db.commit()
    await db.refresh(tmpl)
    return _template_to_dict(tmpl)


@router.patch("/{template_id}")
async def update_template(
    template_id: UUID,
    body: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Update an existing message template."""
    practice_id = user["practice_id"]

    tmpl = (await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.practice_id == practice_id,
        )
    )).scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tmpl, field, value)
    tmpl.updated_at = datetime.now(timezone.utc)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="message_template.update",
        resource_type="message_template",
        resource_id=str(template_id),
        details=f"Updated fields: {', '.join(update_data.keys())}",
    )
    await db.commit()
    await db.refresh(tmpl)
    return _template_to_dict(tmpl)


@router.delete("/{template_id}")
async def deactivate_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Deactivate (soft-delete) a message template."""
    practice_id = user["practice_id"]

    tmpl = (await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.practice_id == practice_id,
        )
    )).scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    tmpl.is_active = False
    tmpl.updated_at = datetime.now(timezone.utc)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="message_template.deactivate",
        resource_type="message_template",
        resource_id=str(template_id),
        details=f"Deactivated template: {tmpl.name}",
    )
    await db.commit()
    return {"message": "Template deactivated", "id": str(template_id)}


@router.get("/preview/{template_id}")
async def preview_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Preview a template with sample variables filled in."""
    practice_id = user["practice_id"]

    tmpl = (await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.practice_id == practice_id,
        )
    )).scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    # Render body with sample values
    rendered_body = tmpl.body
    rendered_subject = tmpl.subject or ""
    for var, sample_val in SAMPLE_VARIABLES.items():
        rendered_body = rendered_body.replace(var, sample_val)
        rendered_subject = rendered_subject.replace(var, sample_val)

    return {
        "template_id": str(tmpl.id),
        "name": tmpl.name,
        "channel": tmpl.channel,
        "subject_preview": rendered_subject if tmpl.subject else None,
        "body_preview": rendered_body,
        "original_body": tmpl.body,
        "variables_used": [v for v in SUPPORTED_VARIABLES if v in tmpl.body],
        "sample_values": SAMPLE_VARIABLES,
    }
