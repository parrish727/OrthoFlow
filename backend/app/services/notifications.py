"""Web Push + SMS Notification service."""
import json
import httpx
from app.core.config import settings

# Push subscriptions stored per user (in production, use a DB table)
_subscriptions: dict[str, list[dict]] = {}
# SMS preferences per user
_sms_prefs: dict[str, str] = {}  # user_id -> phone number


def store_subscription(user_id: str, subscription: dict):
    """Store a push subscription for a user."""
    if user_id not in _subscriptions:
        _subscriptions[user_id] = []
    if subscription not in _subscriptions[user_id]:
        _subscriptions[user_id].append(subscription)


def get_subscriptions(user_id: str) -> list[dict]:
    return _subscriptions.get(user_id, [])


def set_sms_preference(user_id: str, phone: str):
    """Enable SMS notifications for a user."""
    _sms_prefs[user_id] = phone


def remove_sms_preference(user_id: str):
    _sms_prefs.pop(user_id, None)


def get_sms_phone(user_id: str) -> str | None:
    return _sms_prefs.get(user_id)


async def send_push(user_id: str, title: str, body: str, url: str = "/"):
    """Send a push notification to all of a user's subscribed devices."""
    subs = get_subscriptions(user_id)
    payload = json.dumps({"title": title, "body": body, "url": url})

    for sub in subs:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    sub["endpoint"],
                    content=payload,
                    headers={"Content-Type": "application/json", "TTL": "86400"},
                    timeout=10,
                )
        except Exception:
            pass


async def send_sms(phone: str, message: str):
    """Send SMS via Twilio."""
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
                data={
                    "To": phone,
                    "From": settings.TWILIO_PHONE_NUMBER,
                    "Body": message,
                },
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                timeout=10,
            )
    except Exception:
        pass


async def notify(user_id: str, title: str, body: str, url: str = "/"):
    """Send notification via push AND SMS (if enabled)."""
    # Always try push
    await send_push(user_id, title, body, url)

    # SMS fallback if user opted in
    phone = get_sms_phone(user_id)
    if phone:
        await send_sms(phone, f"{title}: {body}")


async def notify_invoice_ready(user_id: str, vendor: str, amount: float, invoice_id: str):
    await notify(user_id, "Invoice Ready for Review", f"{vendor} — ${amount:,.2f}", f"/invoice/{invoice_id}")


async def notify_invoice_approved(user_id: str, vendor: str, amount: float):
    await notify(user_id, "Invoice Approved ✓", f"{vendor} — ${amount:,.2f} syncing to QuickBooks", "/invoices")


async def notify_payment_sent(user_id: str, vendor: str, amount: float):
    await notify(user_id, "Payment Sent", f"${amount:,.2f} to {vendor} via ACH", "/invoices")
