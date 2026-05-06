"""
OrthoFlow AI Worker — async invoice processing pipeline.
Consumes jobs from Redis queue, processes via LLM, updates DB.
"""
import asyncio
from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings


async def process_invoice(ctx, invoice_id: str):
    """
    Pipeline:
    1. Fetch PDF from S3 (minio)
    2. OCR extraction (local: pdf2text, prod: AWS Textract)
    3. LLM classification (ollama locally, Bedrock in prod)
    4. Store coded result + confidence score
    5. Route to approval or auto-approve if high confidence
    """
    # TODO: implement full pipeline
    print(f"Processing invoice: {invoice_id}")
    return {"invoice_id": invoice_id, "status": "processed"}


class WorkerSettings:
    functions = [process_invoice]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)


if __name__ == "__main__":
    async def main():
        redis = await create_pool(WorkerSettings.redis_settings)
        print("⚡ OrthoFlow Worker running...")
        # ARQ worker loop
        from arq.worker import run_worker
        run_worker(WorkerSettings)

    asyncio.run(main())
