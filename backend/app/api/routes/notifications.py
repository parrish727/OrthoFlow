"""Push notification + SMS endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services.notifications import store_subscription, get_subscriptions, set_sms_preference, remove_sms_preference, get_sms_phone

router = APIRouter()


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict


class SMSPreference(BaseModel):
    phone: str


@router.post("/subscribe")
async def subscribe(body: PushSubscription, current_user: dict = Depends(get_current_user)):
    """Register a device for push notifications."""
    store_subscription(current_user["user_id"], body.model_dump())
    return {"status": "subscribed"}


@router.post("/sms/enable")
async def enable_sms(body: SMSPreference, current_user: dict = Depends(get_current_user)):
    """Enable SMS notifications as fallback."""
    set_sms_preference(current_user["user_id"], body.phone)
    return {"status": "sms_enabled", "phone": body.phone}


@router.post("/sms/disable")
async def disable_sms(current_user: dict = Depends(get_current_user)):
    """Disable SMS notifications."""
    remove_sms_preference(current_user["user_id"])
    return {"status": "sms_disabled"}


@router.get("/status")
async def notification_status(current_user: dict = Depends(get_current_user)):
    """Check notification preferences."""
    subs = get_subscriptions(current_user["user_id"])
    phone = get_sms_phone(current_user["user_id"])
    return {
        "push_enabled": len(subs) > 0,
        "push_devices": len(subs),
        "sms_enabled": phone is not None,
        "sms_phone": phone,
    }
