from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    # TODO: implement JWT auth with practice-scoped tokens
    raise HTTPException(status_code=501, detail="Auth not yet implemented")


@router.post("/register")
async def register(body: LoginRequest):
    raise HTTPException(status_code=501, detail="Registration not yet implemented")
