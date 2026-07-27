"""OrthoFlow API — Patient Messages (MyChart-style threaded messaging).

Staff endpoints for viewing patient message threads grouped by patient,
reading full conversations, sending replies, and marking messages as read.
All endpoints use staff JWT (get_current_user) and are practice-scoped.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.portal import PortalMessage
from app.models.clinical import Patient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/patient-messages", tags=["patient-messages"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class MessageCreate(BaseModel):
    subject: str | None = Field(None, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)


class ThreadSummary(BaseModel):
    patient_id: str
    patient_name: str
    last_message_body: str
    last_message_at: str
    last_message_direction: str
    unread_count: int
    total_count: int


class ThreadListResponse(BaseModel):
    total: int
    threads: list[ThreadSummary]


class MessageItem(BaseModel):
    id: str
    direction: str
    subject: str | None
    body: str
    is_read: bool
    read_at: str | None
    sent_by_staff: str | None
    created_at: str


class ThreadDetailResponse(BaseModel):
    patient_id: str
    patient_name: str
    messages: list[MessageItem]
    total: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/threads", response_model=ThreadListResponse)
async def list_message_threads(
    search: str | None = Query(None, description="Search by patient name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List message threads grouped by patient with unread count and last message."""
    practice_id = user["practice_id"]

    # Subquery: get last message timestamp per patient
    last_msg_subquery = (
        select(
            PortalMessage.patient_id,
            func.max(PortalMessage.created_at).label("last_message_at"),
            func.count(PortalMessage.id).label("total_count"),
            func.sum(
                case(
                    (
                        and_(
                            PortalMessage.direction == "from_patient",
                            PortalMessage.is_read == False,  # noqa: E712
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("unread_count"),
        )
        .where(PortalMessage.practice_id == practice_id)
        .group_by(PortalMessage.patient_id)
        .subquery()
    )

    # Main query: join with Patient for names
    query = (
        select(
            Patient.id.label("patient_id"),
            Patient.first_name,
            Patient.last_name,
            last_msg_subquery.c.last_message_at,
            last_msg_subquery.c.total_count,
            last_msg_subquery.c.unread_count,
        )
        .join(last_msg_subquery, Patient.id == last_msg_subquery.c.patient_id)
        .where(Patient.practice_id == practice_id)
    )

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Patient.first_name.ilike(search_filter)) | (Patient.last_name.ilike(search_filter))
        )

    # Count total threads
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Order by most recent message first
    query = query.order_by(last_msg_subquery.c.last_message_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.all()

    # Fetch the last message body for each thread
    threads = []
    for row in rows:
        # Get the most recent message for this patient
        last_msg_result = await db.execute(
            select(PortalMessage.body, PortalMessage.direction)
            .where(
                PortalMessage.practice_id == practice_id,
                PortalMessage.patient_id == row.patient_id,
            )
            .order_by(PortalMessage.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg_result.first()

        threads.append({
            "patient_id": str(row.patient_id),
            "patient_name": f"{row.first_name} {row.last_name}",
            "last_message_body": last_msg.body[:150] if last_msg else "",
            "last_message_at": row.last_message_at.isoformat() if row.last_message_at else "",
            "last_message_direction": last_msg.direction if last_msg else "",
            "unread_count": int(row.unread_count or 0),
            "total_count": int(row.total_count or 0),
        })

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="patient_message.list_threads",
        resource_type="portal_message",
    )

    return {"total": total, "threads": threads}


@router.get("/threads/{patient_id}", response_model=ThreadDetailResponse)
async def get_thread(
    patient_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get full message conversation for a specific patient."""
    practice_id = user["practice_id"]

    # Verify patient exists in this practice
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.practice_id == practice_id,
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Get messages for this patient, ordered chronologically
    query = (
        select(PortalMessage)
        .where(
            PortalMessage.practice_id == practice_id,
            PortalMessage.patient_id == patient_id,
        )
        .order_by(PortalMessage.created_at.asc())
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    messages = result.scalars().all()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="patient_message.view_thread",
        resource_type="portal_message",
        resource_id=patient_id,
        details=f"Viewed thread for patient {patient_id}",
    )

    return {
        "patient_id": str(patient.id),
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "total": total,
        "messages": [
            {
                "id": str(m.id),
                "direction": m.direction,
                "subject": m.subject,
                "body": m.body,
                "is_read": m.is_read,
                "read_at": m.read_at.isoformat() if m.read_at else None,
                "sent_by_staff": str(m.sent_by_staff) if m.sent_by_staff else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/threads/{patient_id}", status_code=status.HTTP_201_CREATED)
async def send_message(
    patient_id: str,
    payload: MessageCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Staff sends a message to a patient."""
    practice_id = user["practice_id"]

    # Verify patient exists in this practice
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.practice_id == practice_id,
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    message = PortalMessage(
        practice_id=practice_id,
        patient_id=patient_id,
        direction="to_patient",
        subject=payload.subject,
        body=payload.body,
        is_read=False,
        sent_by_staff=user["user_id"],
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="patient_message.send",
        resource_type="portal_message",
        resource_id=str(message.id),
        details=f"Staff message to patient {patient_id}",
    )

    logger.info("Patient message sent: message=%s to patient=%s", str(message.id), patient_id)
    return {
        "id": str(message.id),
        "patient_id": str(patient_id),
        "direction": "to_patient",
        "body": message.body,
        "created_at": message.created_at.isoformat(),
    }


@router.patch("/threads/{patient_id}/read")
async def mark_thread_read(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark all unread messages from a patient as read."""
    practice_id = user["practice_id"]

    # Verify patient exists in this practice
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.practice_id == practice_id,
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Find all unread messages from this patient
    unread_result = await db.execute(
        select(PortalMessage).where(
            PortalMessage.practice_id == practice_id,
            PortalMessage.patient_id == patient_id,
            PortalMessage.direction == "from_patient",
            PortalMessage.is_read == False,  # noqa: E712
        )
    )
    unread_messages = unread_result.scalars().all()

    now = datetime.now(timezone.utc)
    marked_count = 0
    for msg in unread_messages:
        msg.is_read = True
        msg.read_at = now
        marked_count += 1

    if marked_count > 0:
        await db.commit()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="patient_message.mark_read",
        resource_type="portal_message",
        resource_id=patient_id,
        details=f"Marked {marked_count} messages as read for patient {patient_id}",
    )

    return {
        "patient_id": str(patient_id),
        "marked_count": marked_count,
    }
