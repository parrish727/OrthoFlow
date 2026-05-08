"""Web Push Notification service — sends push to subscribed devices."""
import json
import httpx
from app.core.config import settings

# Push subscriptions stored per user (in production, use a DB table)
_subscriptions: dict[str, list[dict]] = {}


def store_subscription(user_id: str, subscription: dict):
    """Store a push subscription for a user."""
    if user_id not in _subscriptions:
        _subscriptions[user_id] = []
    # Avoid duplicates
    if subscription not in _subscriptions[user_id]:
        _subscriptions[user_id].append(subscription)


def get_subscriptions(user_id: str) -> list[dict]:
    return _subscriptions.get(user_id, [])


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
            pass  # Subscription may have expired


async def notify_invoice_ready(user_id: str, vendor: str, amount: float, invoice_id: str):
    """Notify when an invoice is ready for review."""
    await send_push(
        user_id=user_id,
        title="Invoice Ready for Review",
        body=f"{vendor} — ${amount:,.2f}",
        url=f"/invoice/{invoice_id}",
    )


async def notify_invoice_approved(user_id: str, vendor: str, amount: float):
    """Notify when an invoice has been approved."""
    await send_push(
        user_id=user_id,
        title="Invoice Approved ✓",
        body=f"{vendor} — ${amount:,.2f} syncing to QuickBooks",
        url="/invoices",
    )


async def notify_payment_sent(user_id: str, vendor: str, amount: float):
    """Notify when a payment has been initiated."""
    await send_push(
        user_id=user_id,
        title="Payment Sent",
        body=f"${amount:,.2f} to {vendor} via ACH",
        url="/invoices",
    )
