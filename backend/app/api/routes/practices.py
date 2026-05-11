from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user

router = APIRouter()


class PracticeCreate(BaseModel):
    name: str
    npi: str | None = None
    address: str | None = None


@router.post("/")
async def create_practice(body: PracticeCreate):
    # TODO: create practice with tenant isolation
    return {"message": "Practice creation not yet implemented"}


@router.get("/")
async def list_practices():
    return {"practices": []}


@router.get("/me")
async def get_my_practice(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's practice info including branding."""
    from app.models.models import Practice
    from sqlalchemy import select
    result = await db.execute(select(Practice).where(Practice.id == current_user["practice_id"]))
    practice = result.scalar_one_or_none()
    if not practice:
        return {"name": "My Practice"}
    return {
        "id": str(practice.id),
        "name": practice.name,
        "address": practice.address,
        "logo_url": practice.logo_url,
        "primary_color": practice.primary_color,
    }
