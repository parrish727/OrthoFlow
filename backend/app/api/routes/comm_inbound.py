"""OrthoFlow API — Inbound SMS Handling (Two-Way Texting).

Twilio webhook for receiving patient SMS responses. Handles:
- YES/CONFIRM → confirm appointment
- CANCEL → cancel appointment
- STOP → immediate TCPA opt-out
Validates Twilio request signature for security.
"""
import base64
import hashlib
import hmac
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import get_db
from app.models.clinical import Appointment, Patient
from app.models.communications import (
    CommunicationPreference,
    MessageLog,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/communications/inbound", tags=["communication-inbound"])


# ── Twilio Signature Validation ───────────────────────────────────────────────

def _validate_twilio_signature(request_url: str, params: dict, signature: str) -> bool:
    """Validate Twilio webhook signature to prevent spoofed requests.

    See: https://www.twilio.com/docs/usage/security#validating-requests
    """
    if not settings.TWILIO_AUTH_TOKEN:
        logger.warning("twilio_auth_token_not_configured")
        return False

    # Build validation string: URL + sorted params
    data = request_url
    for key in sorted(params.keys()):
        data += key + params[key]

    # HMAC-SHA1
    computed = hmac.new(
        settings.TWILIO_AUTH_TOKEN.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha1,
    ).digest()

    expected = base64.b64encode(computed).decode("utf-8")
    return hmac.compare_digest(expected, signature)


# ── TwiML Response Helpers ────────────────────────────────────────────────────

def _twiml_response(message: str | None = None) -> Response:
    """Generate a TwiML XML response."""
    if message:
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f"<Response><Message>{message}</Message></Response>"
        )
    else:
        body = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    return Response(content=body, media_type="application/xml")


# ── Keyword Parsing ───────────────────────────────────────────────────────────

CONFIRM_KEYWORDS = {"yes", "confirm", "y", "confirmed"}
CANCEL_KEYWORDS = {"cancel", "reschedule", "no"}
STOP_KEYWORDS = {"stop", "unsubscribe", "opt-out", "optout", "quit"}


def _parse_intent(body: str) -> str:
    """Parse patient response into an intent category."""
    normalized = body.strip().lower()
    if normalized in CONFIRM_KEYWORDS:
        return "confirm"
    if normalized in CANCEL_KEYWORDS:
        return "cancel"
    if normalized in STOP_KEYWORDS:
        return "stop"
    return "unknown"


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/sms")
async def receive_inbound_sms(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Twilio webhook for inbound SMS. No auth — Twilio calls this directly.

    Validates Twilio signature header, matches sender to patient,
    processes intent (confirm/cancel/stop), and logs the message.
    """
    # Parse form data from Twilio
    form_data = await request.form()
    params = {k: v for k, v in form_data.items()}

    from_number = params.get("From", "")
    message_body = params.get("Body", "")
    twilio_sid = params.get("MessageSid", "")

    if not from_number or not message_body:
        return _twiml_response()

    # Validate Twilio signature
    signature = request.headers.get("X-Twilio-Signature", "")
    request_url = str(request.url)
    if settings.TWILIO_AUTH_TOKEN and not _validate_twilio_signature(request_url, params, signature):
        logger.warning("twilio_signature_invalid", from_number=from_number)
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # Match phone number to patient
    # Look up via communication preferences first, then patient phone
    pref = (await db.execute(
        select(CommunicationPreference).where(
            CommunicationPreference.phone_number == from_number,
        )
    )).scalar_one_or_none()

    patient = None
    practice_id = None

    if pref:
        patient = (await db.execute(
            select(Patient).where(Patient.id == pref.patient_id)
        )).scalar_one_or_none()
        practice_id = str(pref.practice_id)
    else:
        # Search by patient phone number
        patient = (await db.execute(
            select(Patient).where(Patient.phone == from_number)
        )).scalars().first()
        if patient:
            practice_id = str(patient.practice_id)

    if not patient or not practice_id:
        logger.info("inbound_sms_unknown_number", from_number=from_number)
        return _twiml_response()

    # Parse intent
    intent = _parse_intent(message_body)
    response_text = None

    if intent == "stop":
        # TCPA opt-out — immediately disable SMS
        if pref:
            pref.sms_enabled = False
            pref.tcpa_opt_out_date = datetime.now(timezone.utc)
        else:
            # Create preference record with opt-out
            pref = CommunicationPreference(
                practice_id=practice_id,
                patient_id=patient.id,
                phone_number=from_number,
                sms_enabled=False,
                tcpa_opt_out_date=datetime.now(timezone.utc),
            )
            db.add(pref)

        await audit_log(
            db=db,
            practice_id=practice_id,
            user_id=None,
            action="communication_preference.tcpa_opt_out_inbound",
            resource_type="communication_preference",
            resource_id=str(patient.id),
            details=f"Patient opted out via STOP keyword from {from_number}",
        )
        response_text = "You have been unsubscribed. You will no longer receive text messages. Reply START to re-subscribe."

    elif intent == "confirm":
        # Find the most recent upcoming appointment for this patient
        upcoming_appt = (await db.execute(
            select(Appointment).where(
                Appointment.patient_id == patient.id,
                Appointment.practice_id == practice_id,
                Appointment.status == "scheduled",
                Appointment.appointment_date >= datetime.now(timezone.utc).date(),
            ).order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc())
        )).scalars().first()

        if upcoming_appt:
            upcoming_appt.status = "confirmed"
            await audit_log(
                db=db,
                practice_id=practice_id,
                user_id=None,
                action="appointment.confirm_via_sms",
                resource_type="appointment",
                resource_id=str(upcoming_appt.id),
                details=f"Patient confirmed via SMS reply from {from_number}",
            )
            appt_date = upcoming_appt.appointment_date.strftime("%A, %B %d")
            appt_time = upcoming_appt.start_time.strftime("%-I:%M %p")
            response_text = f"Your appointment on {appt_date} at {appt_time} is confirmed. See you then!"
        else:
            response_text = "Thank you for your response."

    elif intent == "cancel":
        # Find upcoming appointment
        upcoming_appt = (await db.execute(
            select(Appointment).where(
                Appointment.patient_id == patient.id,
                Appointment.practice_id == practice_id,
                Appointment.status.in_(["scheduled", "confirmed"]),
                Appointment.appointment_date >= datetime.now(timezone.utc).date(),
            ).order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc())
        )).scalars().first()

        if upcoming_appt:
            upcoming_appt.status = "cancelled"
            await audit_log(
                db=db,
                practice_id=practice_id,
                user_id=None,
                action="appointment.cancel_via_sms",
                resource_type="appointment",
                resource_id=str(upcoming_appt.id),
                details=f"Patient cancelled via SMS reply from {from_number}",
            )
            response_text = "Your appointment has been cancelled. Please call our office to reschedule."
        else:
            response_text = "We could not find an upcoming appointment. Please call our office for assistance."

    # Log inbound message
    msg_log = MessageLog(
        practice_id=practice_id,
        patient_id=patient.id,
        direction="inbound",
        channel="sms",
        to_address=settings.TWILIO_PHONE_NUMBER,
        from_address=from_number,
        body=message_body,
        status="received",
        external_id=twilio_sid,
        metadata_={"intent": intent, "raw_body": message_body},
    )
    db.add(msg_log)

    # If there was a recent outbound message to this patient, update its reply fields
    recent_outbound = (await db.execute(
        select(MessageLog).where(
            MessageLog.patient_id == patient.id,
            MessageLog.practice_id == practice_id,
            MessageLog.direction == "outbound",
            MessageLog.channel == "sms",
            MessageLog.replied_at.is_(None),
        ).order_by(MessageLog.created_at.desc())
    )).scalars().first()

    if recent_outbound:
        recent_outbound.replied_at = datetime.now(timezone.utc)
        recent_outbound.reply_body = message_body

    await db.commit()

    return _twiml_response(response_text)
