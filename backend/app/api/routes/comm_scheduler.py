"""OrthoFlow API — Automated Reminder Scheduling & Sending.

Handles scheduling appointment reminders (24hr + 2hr), immediate sends,
queue processing for background workers, and Twilio SMS delivery via httpx.
"""
import base64
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.clinical import Appointment, Patient
from app.models.communications import (
    CommunicationPreference,
    MessageLog,
    MessageTemplate,
    ScheduledMessage,
)
from app.models.models import Practice

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/communications/reminders", tags=["communication-reminders"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ScheduleForAppointmentResponse(BaseModel):
    appointment_id: str
    reminders_scheduled: int
    messages: list[dict]


class SendNowRequest(BaseModel):
    patient_id: str
    channel: str = Field("sms", pattern="^(sms|email)$")
    template_id: str | None = None
    body: str | None = Field(None, max_length=1600)
    subject: str | None = Field(None, max_length=200)
    appointment_id: str | None = None


class QueueProcessResult(BaseModel):
    processed: int
    sent: int
    failed: int
    skipped: int


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _resolve_template_variables(
    body: str,
    patient: Patient,
    appointment: Appointment | None = None,
    practice: Practice | None = None,
) -> str:
    """Replace template variables with actual values."""
    replacements = {
        "{patient_name}": f"{patient.first_name} {patient.last_name}",
        "{provider_name}": "Your Provider",
        "{office_name}": practice.name if practice else "Our Office",
        "{office_phone}": "",
    }
    if appointment:
        replacements["{appointment_date}"] = appointment.appointment_date.strftime("%A, %B %d")
        replacements["{appointment_time}"] = appointment.start_time.strftime("%-I:%M %p")
    else:
        replacements["{appointment_date}"] = ""
        replacements["{appointment_time}"] = ""

    result = body
    for var, value in replacements.items():
        result = result.replace(var, value)
    return result


async def _send_sms(to: str, body: str, subscriber_id: str = None) -> dict:
    """Send SMS via Novu self-hosted notification platform."""
    from app.api.routes.comm_novu import send_sms, create_subscriber
    
    # If we have a subscriber_id (patient_id), use Novu workflow
    if subscriber_id:
        result = await send_sms(subscriber_id, body)
        if "error" not in result:
            return {"status": "sent", "external_id": result.get("data", {}).get("transactionId")}
        return {"status": "failed", "error": result.get("error", "Novu send failed")}
    
    # Fallback: create a temporary subscriber with the phone number
    temp_id = f"phone-{to.replace('+', '').replace('-', '').replace(' ', '')}"
    await create_subscriber(temp_id, phone=to)
    result = await send_sms(temp_id, body)
    if "error" not in result:
        return {"status": "sent", "external_id": result.get("data", {}).get("transactionId")}
    return {"status": "failed", "error": result.get("error", "Novu send failed")}


async def _send_email(to: str, subject: str, body: str, subscriber_id: str = None) -> dict:
    """Send email via Novu self-hosted notification platform."""
    from app.api.routes.comm_novu import send_email, create_subscriber

    # If we have a subscriber_id (patient_id), use Novu workflow
    if subscriber_id:
        result = await send_email(subscriber_id, subject, body)
        if "error" not in result:
            return {"status": "sent", "external_id": result.get("data", {}).get("transactionId")}
        return {"status": "failed", "error": result.get("error", "Novu send failed")}

    # Fallback: create a temporary subscriber with the email
    temp_id = f"email-{to.replace('@', '-at-').replace('.', '-')}"
    await create_subscriber(temp_id, email=to)
    result = await send_email(temp_id, subject, body)
    if "error" not in result:
        return {"status": "sent", "external_id": result.get("data", {}).get("transactionId")}
    return {"status": "failed", "error": result.get("error", "Novu send failed")}



# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/schedule-for-appointment/{appointment_id}", status_code=status.HTTP_201_CREATED)
async def schedule_for_appointment(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Schedule reminders for an appointment (24hr + 2hr before)."""
    practice_id = user["practice_id"]

    # Fetch appointment
    appt = (await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.practice_id == practice_id,
        )
    )).scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Fetch patient
    patient = (await db.execute(
        select(Patient).where(Patient.id == appt.patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Fetch preferences (or use defaults)
    pref = (await db.execute(
        select(CommunicationPreference).where(
            CommunicationPreference.patient_id == appt.patient_id,
            CommunicationPreference.practice_id == practice_id,
        )
    )).scalar_one_or_none()

    # Check if SMS is opted out
    if pref and not pref.sms_enabled and (not pref or not pref.email_enabled):
        raise HTTPException(
            status_code=400,
            detail="Patient has opted out of all communication channels",
        )

    # Determine channel and address
    channel = pref.preferred_channel if pref else "sms"
    if channel == "sms" and pref and not pref.sms_enabled:
        channel = "email"
    elif channel == "email" and pref and not pref.email_enabled:
        channel = "sms"

    to_address = (pref.phone_number if pref else patient.phone) if channel == "sms" else (pref.email_address if pref else patient.email)
    if not to_address:
        raise HTTPException(status_code=400, detail=f"No {channel} address available for patient")

    # Get default reminder template
    template = (await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.practice_id == practice_id,
            MessageTemplate.template_type == "appointment_reminder",
            MessageTemplate.channel == channel,
            MessageTemplate.is_active.is_(True),
        ).order_by(MessageTemplate.is_default.desc())
    )).scalars().first()

    # Fetch practice for template vars
    practice = (await db.execute(select(Practice).where(Practice.id == practice_id))).scalar_one_or_none()

    # Build appointment datetime
    appt_datetime = datetime.combine(appt.appointment_date, appt.start_time, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    # Default body if no template
    default_body = (
        f"Hi {patient.first_name}, this is a reminder for your appointment on "
        f"{appt.appointment_date.strftime('%A, %B %d')} at {appt.start_time.strftime('%-I:%M %p')}. "
        f"Reply YES to confirm or CANCEL to reschedule."
    )

    reminders = []
    timing_offsets = []

    # 24-hour reminder
    if not pref or pref.reminder_24hr:
        send_at_24hr = appt_datetime - timedelta(hours=24)
        if send_at_24hr > now:
            timing_offsets.append(("24hr", send_at_24hr))

    # 2-hour reminder
    if not pref or pref.reminder_2hr:
        send_at_2hr = appt_datetime - timedelta(hours=2)
        if send_at_2hr > now:
            timing_offsets.append(("2hr", send_at_2hr))

    for timing, send_at in timing_offsets:
        body = default_body
        if template:
            body = _resolve_template_variables(template.body, patient, appt, practice)

        scheduled = ScheduledMessage(
            practice_id=practice_id,
            patient_id=appt.patient_id,
            appointment_id=appt.id,
            template_id=template.id if template else None,
            channel=channel,
            to_address=to_address,
            subject=template.subject if template and channel == "email" else None,
            body=body,
            scheduled_for=send_at,
            status="pending",
        )
        db.add(scheduled)
        reminders.append({
            "timing": timing,
            "scheduled_for": send_at.isoformat(),
            "channel": channel,
        })

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="reminder.schedule",
        resource_type="scheduled_message",
        resource_id=str(appointment_id),
        details=f"Scheduled {len(reminders)} reminders for appointment",
    )
    await db.commit()

    return {
        "appointment_id": str(appointment_id),
        "reminders_scheduled": len(reminders),
        "messages": reminders,
    }


@router.post("/send-now", status_code=status.HTTP_201_CREATED)
async def send_now(
    body: SendNowRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Send a message immediately to a patient."""
    practice_id = user["practice_id"]

    # Fetch patient
    patient = (await db.execute(
        select(Patient).where(Patient.id == body.patient_id, Patient.practice_id == practice_id)
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get preferences
    pref = (await db.execute(
        select(CommunicationPreference).where(
            CommunicationPreference.patient_id == body.patient_id,
            CommunicationPreference.practice_id == practice_id,
        )
    )).scalar_one_or_none()

    # Determine to_address
    if body.channel == "sms":
        if pref and not pref.sms_enabled:
            raise HTTPException(status_code=400, detail="Patient has opted out of SMS")
        to_address = (pref.phone_number if pref else None) or patient.phone
    else:
        if pref and not pref.email_enabled:
            raise HTTPException(status_code=400, detail="Patient has opted out of email")
        to_address = (pref.email_address if pref else None) or patient.email

    if not to_address:
        raise HTTPException(status_code=400, detail=f"No {body.channel} address for patient")

    # Resolve message body
    message_body = body.body
    if body.template_id:
        tmpl = (await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == body.template_id,
                MessageTemplate.practice_id == practice_id,
            )
        )).scalar_one_or_none()
        if not tmpl:
            raise HTTPException(status_code=404, detail="Template not found")
        practice = (await db.execute(select(Practice).where(Practice.id == practice_id))).scalar_one_or_none()

        appt = None
        if body.appointment_id:
            appt = (await db.execute(
                select(Appointment).where(Appointment.id == body.appointment_id)
            )).scalar_one_or_none()

        message_body = _resolve_template_variables(tmpl.body, patient, appt, practice)

    if not message_body:
        raise HTTPException(status_code=400, detail="Message body is required (provide body or template_id)")

    # Send
    if body.channel == "sms":
        result = await _send_sms(to_address, message_body)
    else:
        result = await _send_email(to_address, body.subject or "Message from your orthodontist", message_body)

    # Log message
    msg_log = MessageLog(
        practice_id=practice_id,
        patient_id=body.patient_id,
        appointment_id=body.appointment_id,
        direction="outbound",
        channel=body.channel,
        to_address=to_address,
        from_address=settings.TWILIO_PHONE_NUMBER if body.channel == "sms" else None,
        subject=body.subject,
        body=message_body,
        template_id=body.template_id,
        status=result["status"],
        external_id=result.get("external_id"),
        error_message=result.get("error"),
        delivered_at=datetime.now(timezone.utc) if result["status"] == "sent" else None,
    )
    db.add(msg_log)

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="message.send_now",
        resource_type="message_log",
        resource_id=None,
        details=f"Sent {body.channel} to patient {body.patient_id}: {result['status']}",
    )
    await db.commit()
    await db.refresh(msg_log)

    return {
        "id": str(msg_log.id),
        "status": result["status"],
        "channel": body.channel,
        "to_address": to_address,
        "external_id": result.get("external_id"),
        "error": result.get("error"),
    }


@router.get("/scheduled")
async def list_scheduled_messages(
    status_filter: str | None = Query(None, alias="status"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """List scheduled messages with optional filtering."""
    practice_id = user["practice_id"]
    q = select(ScheduledMessage).where(ScheduledMessage.practice_id == practice_id)

    if status_filter:
        q = q.where(ScheduledMessage.status == status_filter)
    if date_from:
        q = q.where(ScheduledMessage.scheduled_for >= date_from)
    if date_to:
        q = q.where(ScheduledMessage.scheduled_for <= date_to)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(ScheduledMessage.scheduled_for.asc()).offset((page - 1) * size).limit(size)
    result = await db.execute(q)
    messages = result.scalars().all()

    return {
        "scheduled_messages": [
            {
                "id": str(m.id),
                "patient_id": str(m.patient_id),
                "appointment_id": str(m.appointment_id) if m.appointment_id else None,
                "channel": m.channel,
                "to_address": m.to_address,
                "body": m.body,
                "scheduled_for": m.scheduled_for.isoformat(),
                "status": m.status,
                "attempts": m.attempts,
                "error_message": m.error_message,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.delete("/scheduled/{message_id}")
async def cancel_scheduled_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Cancel a scheduled message that hasn't been sent yet."""
    practice_id = user["practice_id"]

    msg = (await db.execute(
        select(ScheduledMessage).where(
            ScheduledMessage.id == message_id,
            ScheduledMessage.practice_id == practice_id,
        )
    )).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Scheduled message not found")

    if msg.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot cancel message with status: {msg.status}")

    msg.status = "cancelled"
    msg.cancelled_reason = "Manually cancelled by user"

    await audit_log(
        db=db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="scheduled_message.cancel",
        resource_type="scheduled_message",
        resource_id=str(message_id),
        details="Scheduled message cancelled by user",
    )
    await db.commit()
    return {"message": "Scheduled message cancelled", "id": str(message_id)}


@router.post("/process-queue")
async def process_queue(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """Process due scheduled messages. Called by background worker."""
    practice_id = user["practice_id"]
    now = datetime.now(timezone.utc)

    # Get all pending messages that are due
    due_messages = (await db.execute(
        select(ScheduledMessage).where(
            ScheduledMessage.practice_id == practice_id,
            ScheduledMessage.status == "pending",
            ScheduledMessage.scheduled_for <= now,
        ).order_by(ScheduledMessage.scheduled_for.asc()).limit(100)
    )).scalars().all()

    processed = 0
    sent = 0
    failed = 0
    skipped = 0

    for msg in due_messages:
        processed += 1

        # Check patient opt-out before sending
        pref = (await db.execute(
            select(CommunicationPreference).where(
                CommunicationPreference.patient_id == msg.patient_id,
                CommunicationPreference.practice_id == practice_id,
            )
        )).scalar_one_or_none()

        if pref and msg.channel == "sms" and not pref.sms_enabled:
            msg.status = "skipped"
            msg.error_message = "Patient opted out of SMS"
            skipped += 1
            continue

        if pref and msg.channel == "email" and not pref.email_enabled:
            msg.status = "skipped"
            msg.error_message = "Patient opted out of email"
            skipped += 1
            continue

        # Send
        msg.attempts += 1
        msg.last_attempt_at = now

        if msg.channel == "sms":
            result = await _send_sms(msg.to_address, msg.body)
        else:
            result = await _send_email(msg.to_address, msg.subject or "", msg.body)

        if result["status"] == "sent":
            msg.status = "sent"
            sent += 1

            # Create message log entry
            log_entry = MessageLog(
                practice_id=practice_id,
                patient_id=msg.patient_id,
                appointment_id=msg.appointment_id,
                direction="outbound",
                channel=msg.channel,
                to_address=msg.to_address,
                from_address=settings.TWILIO_PHONE_NUMBER if msg.channel == "sms" else None,
                subject=msg.subject,
                body=msg.body,
                template_id=msg.template_id,
                status="sent",
                external_id=result.get("external_id"),
                delivered_at=now,
            )
            db.add(log_entry)
        else:
            if msg.attempts >= 3:
                msg.status = "failed"
                msg.error_message = result.get("error", "Max retries exceeded")
            else:
                # Keep pending for retry
                msg.status = "pending"
                msg.error_message = result.get("error")
            failed += 1

    await db.commit()

    return {
        "processed": processed,
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
    }
