"""Redis job queue for async invoice processing."""
import redis.asyncio as redis
from app.core.config import settings

_pool = None


async def _get_redis():
    global _pool
    if _pool is None:
        _pool = redis.from_url(settings.REDIS_URL)
    return _pool


async def enqueue_invoice(invoice_id: str):
    r = await _get_redis()
    await r.lpush("orthoflow:invoices:pending", invoice_id)


async def dequeue_invoice() -> str | None:
    r = await _get_redis()
    result = await r.rpop("orthoflow:invoices:pending")
    return result.decode() if result else None


async def queue_length() -> int:
    r = await _get_redis()
    return await r.llen("orthoflow:invoices:pending")
