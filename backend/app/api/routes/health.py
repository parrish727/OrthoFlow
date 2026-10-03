from fastapi import APIRouter

from app.core import reseed_status

router = APIRouter()


@router.get("/")
async def healthcheck():
    return {"status": "healthy", "service": "orthoflow-ai"}


@router.get("/ready")
async def readiness():
    return {"ready": True}


@router.get("/health/reseed")
async def reseed_health():
    """Status of the demo daily-reseed background task.

    Exposes last success/failure, the ET date last populated, consecutive failures, and a derived
    'healthy'/'stale' flag so an SRE monitor can alert when the demo schedule stops refreshing
    (previously a silent failure that went unnoticed for days).
    """
    return reseed_status.snapshot()
