"""
OrthoFlow AI Worker — async invoice processing pipeline.
Polls Redis queue, processes invoices via OCR + LLM, updates DB.
"""
import asyncio
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.models.models import Invoice, InvoiceStatus
from app.services.storage import download_file
from app.services.queue import dequeue_invoice
from app.services.llm import complete

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("orthoflow.worker")

_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(_url)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

CLASSIFY_PROMPT = """You are an accounts payable specialist for an orthodontic practice.
Given the raw text of a vendor invoice, extract and classify:

1. vendor_name: the company that sent the invoice
2. invoice_number: the invoice/reference number
3. invoice_date: date on the invoice (ISO format)
4. due_date: payment due date (ISO format)
5. total_amount: total amount due (number)
6. line_items: array of items, each with:
   - description: what was purchased
   - quantity: number of units
   - unit_price: price per unit
   - total: line total
   - category: one of [supplies, lab, equipment, services, software, rent, utilities, insurance, other]

Return ONLY valid JSON. No explanation."""


async def process_invoice(invoice_id: str):
    """Full pipeline: fetch PDF → extract text → LLM classify → update DB."""
    async with SessionLocal() as db:
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            log.error(f"Invoice not found: {invoice_id}")
            return

        invoice.status = InvoiceStatus.processing
        await db.commit()

        try:
            # 1. Download from S3
            pdf_bytes = await download_file(invoice.s3_key)

            # 2. Extract text (simple for MVP — upgrade to Textract in prod)
            raw_text = _extract_text(pdf_bytes)
            invoice.raw_text = raw_text

            # 3. LLM classification
            response = await complete(
                prompt=f"Invoice text:\n\n{raw_text[:4000]}",
                system=CLASSIFY_PROMPT,
            )

            # 4. Parse response
            coded = _parse_json(response)
            if coded:
                invoice.vendor_name = coded.get("vendor_name", "Unknown")
                invoice.invoice_number = coded.get("invoice_number")
                invoice.total_amount = float(coded.get("total_amount", 0))
                invoice.coded_json = json.dumps(coded)
                invoice.confidence_score = 0.92  # TODO: implement real confidence scoring
                invoice.status = InvoiceStatus.coded
                log.info(f"✅ Invoice {invoice_id} coded: {invoice.vendor_name} ${invoice.total_amount}")
            else:
                invoice.status = InvoiceStatus.review
                invoice.confidence_score = 0.0
                log.warning(f"⚠️ Invoice {invoice_id} needs manual review")

            await db.commit()

        except Exception as e:
            log.error(f"❌ Failed to process {invoice_id}: {e}")
            invoice.status = InvoiceStatus.review
            await db.commit()


def _extract_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF. MVP uses basic extraction."""
    try:
        # Try pdfplumber if available
        import pdfplumber
        import io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        # Fallback: decode as text (works for text-based PDFs)
        return pdf_bytes.decode("utf-8", errors="replace")[:5000]


def _parse_json(text: str) -> dict | None:
    """Extract JSON from LLM response."""
    try:
        # Try direct parse
        return json.loads(text)
    except json.JSONDecodeError:
        # Try extracting from markdown code block
        if "```" in text:
            block = text.split("```")[1]
            if block.startswith("json"):
                block = block[4:]
            return json.loads(block.strip())
    except Exception:
        pass
    return None


async def worker_loop():
    """Main worker loop — polls queue and processes invoices."""
    log.info("⚡ OrthoFlow Worker running...")

    # Ensure custom classification model exists on startup
    await _ensure_model()

    while True:
        invoice_id = await dequeue_invoice()
        if invoice_id:
            log.info(f"Processing invoice: {invoice_id}")
            await process_invoice(invoice_id)
        else:
            await asyncio.sleep(2)


async def _ensure_model():
    """Create the orthoflow-classify model in Ollama if it doesn't exist."""
    import httpx as _httpx
    client = _httpx.AsyncClient(timeout=300)
    try:
        r = await client.post(f"{settings.OLLAMA_URL}/api/show", json={"name": "orthoflow-classify"})
        if r.status_code == 200:
            log.info("✅ orthoflow-classify model ready")
            await client.aclose()
            return
    except Exception:
        pass

    log.info("Creating orthoflow-classify model...")
    try:
        import os
        training_path = "/app/ml/training_data/ortho_catalog.json"
        if not os.path.exists(training_path):
            log.warning("⚠️ Training data not found, skipping model creation")
            await client.aclose()
            return

        with open(training_path) as f:
            data = json.load(f)

        examples = ""
        for item in data:
            examples += f'\nMESSAGE user {item["input"]}\nMESSAGE assistant {json.dumps(item["output"])}'

        modelfile = f"""FROM {settings.OLLAMA_MODEL}
SYSTEM You are an orthodontic accounts payable specialist. Classify invoice line items into categories. Respond with JSON only.
PARAMETER temperature 0.1
{examples}
"""
        await client.post(f"{settings.OLLAMA_URL}/api/create", json={"name": "orthoflow-classify", "modelfile": modelfile})
        log.info("✅ orthoflow-classify model created")
    except Exception as e:
        log.warning(f"⚠️ Could not create custom model: {e}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(worker_loop())
