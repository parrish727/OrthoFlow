"""OrthoFlow API — Communication Dashboard & Message Log.

Provides message history, delivery stats, and Twilio status webhook
for delivery confirmation tracking.
"""
from datetime import datetime, timezone
from uuid import UUID

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.communications import MessageLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/communications/messages", tags=["communication-messages"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class MessageDetail(BaseModel):
    id: str
    patient_id: str
    appointment_id: str | None
    direction: str
    channel: str
    to_address: str
    from_address: str | None
    subject: str | None
    body: str
    status: str
    external_id: str | None
    error_message: str | None
    delivered_at: str | None
    replied_at: str | None
    reply_body: str | None
    created_at: str


class DeliveryStats(BaseModel):
    total_sent: int
    delivered: int
    failed: int
    replied: int
    pending: int
    confirmation_rate: float
    delivery_rate: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def _message_to_dict(msg: MessageLog) -> dict:
    return {
        "id": str(msg.id),
        "patient_id": str(msg.patient_id),
        "appointment_id": str(msg.appointment_id) if msg.appointment_id else None,
        "direction": msg.direction,
        "channel": msg.channel,
        "to_address": msg.to_address,
        "from_address": msg.from_address,
        "subject": msg.subject,
        "body": msg.body,
        "template_id": str(msg.template_id) if msg.template_id else None,
        "status": msg.status,
        "external_id": msg.external_id,
        "error_message": msg.error_message,
        "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
        "replied_at": msg.replied_at.isoformat() if msg.replied_at else None,
        "reply_body": msg.reply_body,
        "metadata": msg.metadata_,
        "created_at": msg.created_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
async def list_messages(
    patient_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    channel: str | None = None,
    direction: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """List message log with filtering and pagination."""
    practice_id = user["practice_id"]
    q = select(MessageLog).where(MessageLog.practice_id == practice_id)

    if patient_id:
        q = q.where(MessageLog.patient_id == patient_id)
    if status_filter:
        q = q.where(MessageLog.status == status_filter)
    if channel:
        q = q.where(MessageLog.channel == channel)
    if direction:
        q = q.where(MessageLog.direction == direction)
    if date_from:
        q = q.where(MessageLog.created_at >= date_from)
    if date_to:
        q = q.where(MessageLog.created_at <= date_to)

    # Total count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginated results
    q = q.order_by(MessageLog.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(q)
    messages = result.scalars().all()

    return {
        "messages": [_message_to_dict(m) for m in messages],
        "total": total,
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size,
    }


@router.get("/stats")
async def get_delivery_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Get delivery statistics for the practice over the specified time period."""
    practice_id = user["practice_id"]
    since = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    from datetime import timedelta
    since = since - timedelta(days=days)

    # Outbound messages only for delivery stats
    base_filter = [
        MessageLog.practice_id == practice_id,
        MessageLog.direction == "outbound",
        MessageLog.created_at >= since,
    ]

    # Aggregate counts by status
    stats_q = select(
        func.count().label("total_sent"),
        func.count().filter(MessageLog.status == "delivered").label("delivered"),
        func.count().filter(MessageLog.status == "sent").label("sent_pending"),
        func.count().filter(MessageLog.status == "failed").label("failed"),
        func.count().filter(MessageLog.replied_at.is_not(None)).label("replied"),
        func.count().filter(MessageLog.status.in_(["queued", "pending"])).label("pending"),
    ).where(*base_filter)

    row = (await db.execute(stats_q)).one()

    total_sent = row.total_sent or 0
    delivered = row.delivered or 0
    sent_pending = row.sent_pending or 0
    failed = row.failed or 0
    replied = row.replied or 0
    pending = row.pending or 0

    # Confirmation rate = replied / (delivered + sent_pending) where reply indicates confirmation
    successful = delivered + sent_pending
    confirmation_rate = (replied / successful * 100) if successful > 0 else 0.0
    delivery_rate = ((delivered + sent_pending) / total_sent * 100) if total_sent > 0 else 0.0

    return {
        "period_days": days,
        "total_sent": total_sent,
        "delivered": delivered + sent_pending,
        "failed": failed,
        "replied": replied,
        "pending": pending,
        "confirmation_rate": round(confirmation_rate, 1),
        "delivery_rate": round(delivery_rate, 1),
    }


@router.get("/{message_id}")
async def get_message_detail(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Get a single message detail."""
    practice_id = user["practice_id"]

    msg = (await db.execute(
        select(MessageLog).where(
            MessageLog.id == message_id,
            MessageLog.practice_id == practice_id,
        )
    )).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    return _message_to_dict(msg)


@router.post("/webhook/status")
async def twilio_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Twilio delivery status webhook — updates message delivery status.

    No auth — Twilio calls this directly. Matches by external_id (MessageSid).
    """
    form_data = await request.form()
    params = {k: v for k, v in form_data.items()}

    message_sid = params.get("MessageSid", "")
    message_status = params.get("MessageStatus", "")
    error_code = params.get("ErrorCode")
    error_message = params.get("ErrorMessage")

    if not message_sid or not message_status:
        return {"status": "ignored", "reason": "missing required fields"}

    # Find the message by external_id
    msg = (await db.execute(
        select(MessageLog).where(MessageLog.external_id == message_sid)
    )).scalar_one_or_none()

    if not msg:
        logger.info("twilio_status_unknown_sid", message_sid=message_sid)
        return {"status": "ignored", "reason": "message not found"}

    # Map Twilio statuses to our statuses
    status_map = {
        "queued": "queued",
        "sent": "sent",
        "delivered": "delivered",
        "undelivered": "failed",
        "failed": "failed",
        "read": "delivered",
    }

    new_status = status_map.get(message_status, msg.status)
    msg.status = new_status

    if new_status == "delivered" and not msg.delivered_at:
        msg.delivered_at = datetime.now(timezone.utc)

    if new_status == "failed":
        msg.error_message = error_message or f"Twilio error code: {error_code}"

    await audit_log(
        db=db,
        practice_id=str(msg.practice_id),
        user_id=None,
        action="message.status_update",
        resource_type="message_log",
        resource_id=str(msg.id),
        details=f"Twilio status: {message_status} → {new_status}",
    )
    await db.commit()

    return {"status": "processed", "message_id": str(msg.id), "new_status": new_status}
