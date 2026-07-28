"""Stedi Webhook Receiver — handles claim status (277) and ERA (835) events."""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.audit import audit_log
from app.models.claims import InsuranceClaim
from app.services.appeal_automation import process_denial

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

STEDI_WEBHOOK_SECRET = os.environ.get("STEDI_WEBHOOK_SECRET", "")


class StediWebhookPayload(BaseModel):
    """Stedi webhook event payload."""
    event_type: str = Field(..., description="Event type: claim_status_change, era_received")
    claim_id: str | None = None
    status: str | None = None
    payer_claim_number: str | None = None
    denial_codes: list[str] | None = None
    denial_reason: str | None = None
    paid_amount: float | None = None
    adjudication_date: str | None = None
    era_trace_number: str | None = None
    payer_name: str | None = None
    payment_date: str | None = None
    claims: list[dict] | None = None
    raw_payload: dict | None = None


def _verify_webhook_signature(payload_bytes: bytes, signature: str) -> bool:
    """Verify the webhook signature from Stedi using HMAC-SHA256."""
    if not STEDI_WEBHOOK_SECRET:
        logger.warning("STEDI_WEBHOOK_SECRET not configured — skipping signature verification")
        return True

    expected = hmac.new(
        STEDI_WEBHOOK_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/stedi")
async def receive_stedi_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Receive Stedi webhook events (claim status 277, ERA 835).

    Must respond 200 quickly — heavy processing runs in background tasks.
    """
    # Read raw body for signature verification
    body_bytes = await request.body()
    signature = request.headers.get("x-stedi-signature", "")

    if not _verify_webhook_signature(body_bytes, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    try:
        import json
        payload_data = json.loads(body_bytes)
        payload = StediWebhookPayload(**payload_data)
    except Exception as e:
        logger.error(f"Failed to parse Stedi webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload format")

    event_type = payload.event_type
    logger.info(f"Stedi webhook received: {event_type} for claim {payload.claim_id}")

    if event_type == "claim_status_change":
        await _handle_claim_status(payload, background_tasks, db)
    elif event_type == "era_received":
        await _handle_era_received(payload, db)
    else:
        logger.warning(f"Unknown Stedi webhook event type: {event_type}")
        await audit_log(
            db, "system", None, "webhook.stedi.unknown_event",
            "webhook", None,
            details=f"Unknown event type: {event_type}",
        )
        await db.commit()

    return {"status": "ok", "event_type": event_type}


async def _handle_claim_status(
    payload: StediWebhookPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> None:
    """Process a claim status change (277 transaction)."""
    if not payload.claim_id:
        logger.warning("Claim status webhook received without claim_id")
        return

    # Find the claim in our database
    claim = (await db.execute(
        select(InsuranceClaim).where(InsuranceClaim.id == payload.claim_id)
    )).scalar_one_or_none()

    if not claim:
        # Try matching by claim_number (payer reference)
        if payload.payer_claim_number:
            claim = (await db.execute(
                select(InsuranceClaim).where(InsuranceClaim.claim_number == payload.payer_claim_number)
            )).scalar_one_or_none()

    if not claim:
        logger.warning(f"Stedi webhook: claim {payload.claim_id} not found in database")
        await audit_log(
            db, "system", None, "webhook.stedi.claim_not_found",
            "insurance_claim", payload.claim_id,
            details=f"Status: {payload.status}, payer_claim: {payload.payer_claim_number}",
        )
        await db.commit()
        return

    # Update claim status
    old_status = claim.status
    new_status = _map_stedi_status(payload.status or "")

    claim.status = new_status
    if payload.payer_claim_number:
        claim.claim_number = payload.payer_claim_number
    if payload.paid_amount is not None:
        claim.total_paid = payload.paid_amount
    if payload.denial_codes:
        claim.denial_codes = payload.denial_codes
    if payload.denial_reason:
        claim.denial_reason = payload.denial_reason
    if payload.adjudication_date:
        claim.adjudication_date = datetime.fromisoformat(payload.adjudication_date)

    claim.updated_at = datetime.now(timezone.utc)

    await audit_log(
        db, str(claim.practice_id), None, "webhook.stedi.status_update",
        "insurance_claim", str(claim.id),
        details=f"Status changed: {old_status} → {new_status}",
    )
    await db.commit()

    # If denied, trigger same-day appeal in background
    if new_status == "denied":
        logger.info(f"Claim {claim.id} denied — scheduling appeal review")
        background_tasks.add_task(
            _process_denial_background,
            claim_id=str(claim.id),
            practice_id=str(claim.practice_id),
        )


async def _handle_era_received(payload: StediWebhookPayload, db: AsyncSession) -> None:
    """Process an ERA/835 remittance event."""
    if not payload.claims:
        logger.warning("ERA webhook received without claims data")
        return

    for era_claim in payload.claims:
        claim_id = era_claim.get("claim_id")
        if not claim_id:
            continue

        claim = (await db.execute(
            select(InsuranceClaim).where(InsuranceClaim.id == claim_id)
        )).scalar_one_or_none()

        if not claim:
            continue

        # Update payment info from ERA
        if era_claim.get("paid") is not None:
            claim.total_paid = era_claim["paid"]
        if era_claim.get("allowed") is not None:
            claim.total_allowed = era_claim["allowed"]
        if era_claim.get("patient_resp") is not None:
            claim.patient_responsibility = era_claim["patient_resp"]
        if payload.era_trace_number:
            claim.era_reference = payload.era_trace_number

        # Mark as paid if payment received
        if era_claim.get("paid") and era_claim["paid"] > 0:
            claim.status = "paid"
        elif era_claim.get("paid") == 0:
            claim.status = "denied"

        claim.updated_at = datetime.now(timezone.utc)

    await audit_log(
        db, "system", None, "webhook.stedi.era_received",
        "era", payload.era_trace_number,
        details=f"Payer: {payload.payer_name}, claims processed: {len(payload.claims)}",
    )
    await db.commit()


async def _process_denial_background(claim_id: str, practice_id: str) -> None:
    """Background task to process a denial — needs its own DB session."""
    from app.core.database import SessionLocal

    async with SessionLocal() as db:
        try:
            result = await process_denial(claim_id, practice_id, db)
            logger.info(f"Appeal automation result for {claim_id}: {result.get('action')}")
        except Exception as e:
            logger.error(f"Appeal automation failed for {claim_id}: {e}")
            await audit_log(
                db, practice_id, None, "appeal.automation_error",
                "insurance_claim", claim_id,
                details=f"Error: {str(e)[:200]}",
            )
            await db.commit()


def _map_stedi_status(stedi_status: str) -> str:
    """Map Stedi status strings to OrthoFlow ClaimStatus values."""
    mapping = {
        "accepted": "accepted",
        "in_process": "submitted",
        "pending": "submitted",
        "finalized": "paid",
        "paid": "paid",
        "denied": "denied",
        "rejected": "rejected",
    }
    return mapping.get(stedi_status.lower(), "submitted")
