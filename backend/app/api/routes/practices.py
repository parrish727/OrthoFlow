from fastapi import APIRouter
from pydantic import BaseModel

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
