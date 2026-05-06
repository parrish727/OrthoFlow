from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def healthcheck():
    return {"status": "healthy", "service": "orthoflow-ai"}


@router.get("/ready")
async def readiness():
    return {"ready": True}
