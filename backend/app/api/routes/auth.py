from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import hash_password, verify_password, create_token, get_current_user
from app.models.models import User, Practice, UserRole

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    practice_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    practice_id: str
    role: str


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create practice
    practice = Practice(id=uuid4(), name=body.practice_name)
    db.add(practice)

    # Create user
    user = User(
        id=uuid4(),
        practice_id=practice.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.owner,
    )
    db.add(user)
    await db.commit()

    token = create_token(str(user.id), str(practice.id), user.role.value)
    return TokenResponse(access_token=token, practice_id=str(practice.id), role=user.role.value)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(str(user.id), str(user.practice_id), user.role.value)
    return TokenResponse(access_token=token, practice_id=str(user.practice_id), role=user.role.value)


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
