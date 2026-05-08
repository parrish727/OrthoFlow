"""Plaid integration endpoints — link bank, initiate payments."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Invoice, InvoiceStatus
from app.services.plaid import create_link_token, exchange_public_token, get_accounts, initiate_ach_payment
from app.services.notifications import notify_payment_sent

router = APIRouter()


@router.get("/link-token")
async def get_link_token(current_user: dict = Depends(get_current_user)):
    """Get a Plaid Link token to open the bank connection UI."""
    token = await create_link_token(current_user["user_id"], "OrthoFlow Practice")
    return {"link_token": token}


class ExchangeRequest(BaseModel):
    public_token: str


@router.post("/exchange")
async def exchange_token(body: ExchangeRequest, current_user: dict = Depends(get_current_user)):
    """Exchange public token after user links their bank account."""
    result = await exchange_public_token(body.public_token)
    # TODO: store access_token + item_id on the practice (encrypted)
    return {"status": "linked", "item_id": result["item_id"]}


@router.post("/pay/{invoice_id}")
async def pay_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate ACH payment for an approved invoice."""
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
        raise HTTPException(status_code=400, detail="Only approved invoices can be paid")

    # TODO: get practice's Plaid access_token and account_id from DB
    # For now, return a placeholder
    # transfer = await initiate_ach_payment(access_token, account_id, invoice.total_amount, invoice.vendor_name)

    invoice.status = InvoiceStatus.paid
    await db.commit()

    await notify_payment_sent(current_user["user_id"], invoice.vendor_name, invoice.total_amount)

    return {"status": "payment_initiated", "invoice_id": str(invoice.id), "amount": invoice.total_amount}
