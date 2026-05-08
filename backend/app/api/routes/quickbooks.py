"""QuickBooks integration endpoints — OAuth connect, callback, sync."""
import json
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Practice, Invoice, InvoiceStatus
from app.services.quickbooks import get_auth_url, exchange_code, create_bill, refresh_token

router = APIRouter()

# In-memory state store for OAuth (use Redis in production)
_oauth_states: dict[str, str] = {}


@router.get("/connect")
async def connect_quickbooks(current_user: dict = Depends(get_current_user)):
    """Initiate QuickBooks OAuth2 flow. Returns the authorization URL."""
    state = str(uuid4())
    _oauth_states[state] = current_user["practice_id"]
    auth_url = get_auth_url(state)
    return {"auth_url": auth_url}


@router.get("/callback")
async def quickbooks_callback(
    code: str,
    state: str,
    realmId: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth2 callback from QuickBooks. Stores tokens on the practice."""
    practice_id = _oauth_states.pop(state, None)
    if not practice_id:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    # Exchange code for tokens
    tokens = await exchange_code(code)

    # Store tokens on the practice (encrypted in production)
    result = await db.execute(select(Practice).where(Practice.id == practice_id))
    practice = result.scalar_one_or_none()
    if not practice:
        raise HTTPException(status_code=404, detail="Practice not found")

    # Store as JSON in a field (add qbo_tokens column, or use a separate table)
    # For now, store in the address field as a workaround until migration
    # TODO: add proper qbo_tokens column via Alembic migration
    practice.npi = json.dumps({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "realm_id": realmId,
        "expires_in": tokens.get("expires_in", 3600),
    })
    await db.commit()

    # Redirect back to the app settings page
    return RedirectResponse("https://app.orthoflowsolutions.com/settings?qbo=connected")


@router.post("/sync/{invoice_id}")
async def sync_invoice_to_quickbooks(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync an approved invoice to QuickBooks as a Bill."""
    # Get practice QBO tokens
    result = await db.execute(select(Practice).where(Practice.id == current_user["practice_id"]))
    practice = result.scalar_one_or_none()
    if not practice or not practice.npi:
        raise HTTPException(status_code=400, detail="QuickBooks not connected. Go to Settings to connect.")

    try:
        qbo_creds = json.loads(practice.npi)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="QuickBooks not connected")

    # Get the invoice
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.practice_id == current_user["practice_id"],
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != InvoiceStatus.approved:
        raise HTTPException(status_code=400, detail="Only approved invoices can be synced")

    # Build invoice data for QBO
    coded = json.loads(invoice.coded_json) if invoice.coded_json else {"line_items": []}
    invoice_data = {
        "vendor_name": invoice.vendor_name,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "line_items": coded.get("line_items", []),
    }

    # Create bill in QBO
    try:
        qbo_bill = await create_bill(
            access_token=qbo_creds["access_token"],
            realm_id=qbo_creds["realm_id"],
            invoice_data=invoice_data,
        )
    except Exception as e:
        # Try refreshing token
        try:
            new_tokens = await refresh_token(qbo_creds["refresh_token"])
            qbo_creds["access_token"] = new_tokens["access_token"]
            qbo_creds["refresh_token"] = new_tokens["refresh_token"]
            practice.npi = json.dumps(qbo_creds)
            await db.commit()
            qbo_bill = await create_bill(
                access_token=qbo_creds["access_token"],
                realm_id=qbo_creds["realm_id"],
                invoice_data=invoice_data,
            )
        except Exception as retry_err:
            raise HTTPException(status_code=502, detail=f"QuickBooks sync failed: {retry_err}")

    # Mark as paid/synced
    invoice.status = InvoiceStatus.paid
    await db.commit()

    return {"status": "synced", "qbo_bill_id": qbo_bill.get("Bill", {}).get("Id")}


@router.get("/status")
async def quickbooks_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if QuickBooks is connected for this practice."""
    result = await db.execute(select(Practice).where(Practice.id == current_user["practice_id"]))
    practice = result.scalar_one_or_none()
    if not practice or not practice.npi:
        return {"connected": False}
    try:
        creds = json.loads(practice.npi)
        return {"connected": True, "realm_id": creds.get("realm_id")}
    except (json.JSONDecodeError, TypeError):
        return {"connected": False}
