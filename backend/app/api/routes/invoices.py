from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Invoice, InvoiceStatus
from app.services.storage import upload_file
from app.services.queue import enqueue_invoice
from app.services.scanner import scan_file

router = APIRouter()


class InvoiceOut(BaseModel):
    id: str
    vendor_name: str
    invoice_number: str | None
    total_amount: float
    status: str
    confidence_score: float | None
    created_at: str


@router.post("/upload")
async def upload_invoice(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF/image invoice for AI processing."""
    invoice_id = uuid4()
    s3_key = f"{current_user['practice_id']}/{invoice_id}/{file.filename}"

    # Read and scan file for malware
    content = await file.read()
    scan_result = await scan_file(content, file.filename or "upload")
    if not scan_result["clean"]:
        raise HTTPException(status_code=400, detail=f"File rejected: {scan_result['reason']}")

    # Upload to S3/MinIO
    await upload_file(s3_key, content, file.content_type or "application/pdf")

    # Create invoice record
    invoice = Invoice(
        id=invoice_id,
        practice_id=current_user["practice_id"],
        vendor_name="Processing...",
        status=InvoiceStatus.pending,
        s3_key=s3_key,
    )
    db.add(invoice)
    await db.commit()

    # Queue for AI processing
    await enqueue_invoice(str(invoice_id))

    return {"id": str(invoice_id), "status": "queued", "filename": file.filename}


@router.get("/")
async def list_invoices(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List invoices for the authenticated practice."""
    result = await db.execute(
        select(Invoice)
        .where(Invoice.practice_id == current_user["practice_id"])
        .order_by(Invoice.created_at.desc())
        .limit(50)
    )
    invoices = result.scalars().all()
    return {
        "invoices": [
            {
                "id": str(i.id),
                "vendor_name": i.vendor_name,
                "invoice_number": i.invoice_number,
                "total_amount": i.total_amount,
                "status": i.status.value,
                "confidence_score": i.confidence_score,
                "created_at": i.created_at.isoformat() if i.created_at else "",
            }
            for i in invoices
        ]
    }


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.practice_id == current_user["practice_id"],
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {
        "id": str(invoice.id),
        "vendor_name": invoice.vendor_name,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "total_amount": invoice.total_amount,
        "status": invoice.status.value,
        "confidence_score": invoice.confidence_score,
        "coded_json": invoice.coded_json,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else "",
    }


@router.post("/{invoice_id}/approve")
async def approve_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.practice_id == current_user["practice_id"],
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.status = InvoiceStatus.approved
    invoice.approved_by = current_user["user_id"]
    invoice.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(invoice.id), "status": "approved"}


@router.post("/{invoice_id}/reject")
async def reject_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.practice_id == current_user["practice_id"],
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.status = InvoiceStatus.rejected
    await db.commit()
    return {"id": str(invoice.id), "status": "rejected"}
