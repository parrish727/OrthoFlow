from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

router = APIRouter()


class InvoiceResponse(BaseModel):
    id: str
    vendor_name: str
    total_amount: float
    status: str


@router.post("/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """Upload a PDF/image invoice for AI processing."""
    # TODO: save to S3 (minio), queue for worker processing
    return {"message": f"Received {file.filename}", "status": "queued"}


@router.get("/")
async def list_invoices():
    """List invoices for the authenticated practice."""
    return {"invoices": []}


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: str):
    return {"invoice_id": invoice_id, "status": "not_found"}


@router.post("/{invoice_id}/approve")
async def approve_invoice(invoice_id: str):
    """Approve a coded invoice — triggers payment scheduling."""
    return {"invoice_id": invoice_id, "action": "approved"}


@router.post("/{invoice_id}/reject")
async def reject_invoice(invoice_id: str):
    return {"invoice_id": invoice_id, "action": "rejected"}
