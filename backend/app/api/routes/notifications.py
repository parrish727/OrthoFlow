"""Push notification endpoints — subscribe/unsubscribe devices."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services.notifications import store_subscription, get_subscriptions

router = APIRouter()


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict


@router.post("/subscribe")
async def subscribe(body: PushSubscription, current_user: dict = Depends(get_current_user)):
    """Register a device for push notifications."""
    store_subscription(current_user["user_id"], body.model_dump())
    return {"status": "subscribed"}


@router.get("/status")
async def push_status(current_user: dict = Depends(get_current_user)):
    """Check if user has push notifications enabled."""
    subs = get_subscriptions(current_user["user_id"])
    return {"enabled": len(subs) > 0, "devices": len(subs)}
