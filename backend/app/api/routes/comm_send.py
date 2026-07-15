"""OrthoFlow — Message Delivery via Twilio (SMS + Email).

Twilio handles both channels:
- SMS: Twilio Messaging API
- Email: Twilio SendGrid API

No middleware, no Novu, no Google Workspace. Client messages stay
on Twilio infrastructure — isolated from internal systems.
"""
import os
import base64
import logging
import httpx

logger = logging.getLogger(__name__)

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE_NUMBER", "")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@orthoflowsolutions.com")


async def send_sms(to: str, body: str) -> dict:
    """Send SMS via Twilio Messaging API."""
    if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_PHONE:
        logger.warning("twilio_not_configured")
        return {"status": "failed", "error": "Twilio not configured. Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER to .env"}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    auth = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                url,
                data={"To": to, "From": TWILIO_PHONE, "Body": body},
                headers={"Authorization": f"Basic {auth}"},
            )
            if resp.status_code >= 400:
                error = resp.json().get("message", resp.text[:200])
                logger.error(f"twilio_sms_error: {error}")
                return {"status": "failed", "error": error}
            data = resp.json()
            return {"status": "sent", "external_id": data.get("sid")}
        except Exception as e:
            logger.error(f"twilio_sms_exception: {e}")
            return {"status": "failed", "error": str(e)[:200]}


async def send_email(to: str, subject: str, body: str) -> dict:
    """Send Email via Twilio SendGrid API."""
    if not SENDGRID_API_KEY:
        logger.warning("sendgrid_not_configured")
        return {"status": "failed", "error": "SendGrid not configured. Add SENDGRID_API_KEY to .env"}

    # Unsubscribe footer
    unsubscribe_url = f"https://app.orthoflowsolutions.com/portal?action=unsubscribe&email={to}"
    html_body = f"""<div style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;">
<div style="padding:20px;">{body.replace(chr(10), '<br>')}</div>
<div style="border-top:1px solid #e5e7eb;padding:16px 20px;margin-top:20px;">
<p style="font-size:11px;color:#9ca3af;margin:0;">
You received this because you opted in to communications from your orthodontist.
<br><a href="{unsubscribe_url}" style="color:#6b7280;text-decoration:underline;">Unsubscribe</a>
</p></div></div>"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to}]}],
                    "from": {"email": FROM_EMAIL, "name": "OrthoFlow"},
                    "subject": subject,
                    "content": [
                        {"type": "text/plain", "value": body + f"\n\nUnsubscribe: {unsubscribe_url}"},
                        {"type": "text/html", "value": html_body},
                    ],
                },
            )
            if resp.status_code >= 400:
                logger.error(f"sendgrid_error: {resp.status_code} {resp.text[:200]}")
                return {"status": "failed", "error": f"SendGrid error: {resp.status_code}"}
            return {"status": "sent", "external_id": resp.headers.get("X-Message-Id", "")}
        except Exception as e:
            logger.error(f"sendgrid_exception: {e}")
            return {"status": "failed", "error": str(e)[:200]}
