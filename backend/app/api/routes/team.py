"""Team management endpoints — staff invite, role changes, deactivation."""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, hash_password, require_role
from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import get_db
from app.models.models import User
from app.models.portal import TeamInvite

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/team")

VALID_ROLES = {"owner", "doctor", "office_manager", "dental_assistant", "front_desk", "bookkeeper"}


# ── Schemas ───────────────────────────────────────────────────────────────────


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(..., min_length=1, max_length=30)


class AcceptInviteRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class RoleChangeRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=30)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/")
async def list_staff(
    user: dict = Depends(require_role("owner", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all staff members for the practice."""
    result = await db.execute(
        select(User)
        .where(User.practice_id == user["practice_id"])
        .order_by(User.created_at.desc())
    )
    staff = result.scalars().all()

    await audit_log(
        db,
        practice_id=user["practice_id"],
        user_id=user["user_id"],
        action="team.list",
        resource_type="team",
    )
    await db.commit()

    return {
        "staff": [
            {
                "id": str(s.id),
                "full_name": s.full_name,
                "email": s.email,
                "role": s.role,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in staff
        ]
    }


@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_staff(
    payload: InviteRequest,
    user: dict = Depends(require_role("owner", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Invite a new staff member by email. Token expires in 7 days."""
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )

    # Check if user already exists with this email in the practice
    existing = await db.execute(
        select(User).where(User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Check for existing pending invite
    existing_invite = await db.execute(
        select(TeamInvite).where(
            TeamInvite.practice_id == user["practice_id"],
            TeamInvite.email == payload.email,
            TeamInvite.status == "pending",
        )
    )
    if existing_invite.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invite already exists for this email",
        )

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    invite = TeamInvite(
        practice_id=user["practice_id"],
        email=payload.email,
        role=payload.role,
        invited_by=user["user_id"],
        token=token,
        status="pending",
        expires_at=expires_at,
    )
    db.add(invite)

    await audit_log(
        db,
        practice_id=user["practice_id"],
        user_id=user["user_id"],
        action="team.invite",
        resource_type="team_invite",
        resource_id=str(invite.id),
        details=f"Invited {payload.email} as {payload.role}",
    )
    await db.commit()

    invite_link = f"{settings.CORS_ORIGINS[0]}/accept-invite?token={token}"

    logger.info("Team invite created for %s in practice %s", payload.email, user["practice_id"])

    return {
        "invite_id": str(invite.id),
        "email": payload.email,
        "role": payload.role,
        "invite_link": invite_link,
        "expires_at": expires_at.isoformat(),
    }


@router.post("/accept-invite")
async def accept_invite(
    payload: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Accept a team invite — creates the user account."""
    result = await db.execute(
        select(TeamInvite).where(
            TeamInvite.token == payload.token,
            TeamInvite.status == "pending",
        )
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite token",
        )

    if invite.expires_at < datetime.now(timezone.utc):
        invite.status = "expired"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invite has expired. Please request a new one.",
        )

    # Check email not already taken
    existing = await db.execute(
        select(User).where(User.email == invite.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Create the user
    new_user = User(
        practice_id=invite.practice_id,
        email=invite.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=invite.role,
        is_active=True,
    )
    db.add(new_user)

    # Mark invite as accepted
    invite.status = "accepted"
    invite.accepted_at = datetime.now(timezone.utc)

    await audit_log(
        db,
        practice_id=str(invite.practice_id),
        user_id=str(new_user.id),
        action="team.accept_invite",
        resource_type="user",
        resource_id=str(new_user.id),
        details=f"Accepted invite as {invite.role}",
    )
    await db.commit()

    logger.info("Invite accepted: %s joined practice %s as %s", invite.email, invite.practice_id, invite.role)

    return {"message": "Account created successfully", "email": invite.email, "role": invite.role}


@router.patch("/{user_id}/role")
async def change_role(
    user_id: str,
    payload: RoleChangeRequest,
    user: dict = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change a staff member's role. Owner only."""
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.practice_id == user["practice_id"],
        )
    )
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(target_user.id) == user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    old_role = target_user.role
    target_user.role = payload.role

    await audit_log(
        db,
        practice_id=user["practice_id"],
        user_id=user["user_id"],
        action="team.change_role",
        resource_type="user",
        resource_id=user_id,
        details=f"Role changed from {old_role} to {payload.role}",
    )
    await db.commit()

    logger.info("Role changed for user %s: %s → %s", user_id, old_role, payload.role)

    return {"user_id": user_id, "old_role": old_role, "new_role": payload.role}


@router.patch("/{user_id}/deactivate")
async def deactivate_staff(
    user_id: str,
    user: dict = Depends(require_role("owner", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deactivate a staff member."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.practice_id == user["practice_id"],
        )
    )
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(target_user.id) == user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    target_user.is_active = False

    await audit_log(
        db,
        practice_id=user["practice_id"],
        user_id=user["user_id"],
        action="team.deactivate",
        resource_type="user",
        resource_id=user_id,
        details=f"Deactivated user {target_user.email}",
    )
    await db.commit()

    logger.info("User deactivated: %s in practice %s", target_user.email, user["practice_id"])

    return {"user_id": user_id, "is_active": False}


@router.get("/invites")
async def list_invites(
    user: dict = Depends(require_role("owner", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List pending invites for the practice."""
    result = await db.execute(
        select(TeamInvite).where(
            TeamInvite.practice_id == user["practice_id"],
            TeamInvite.status == "pending",
        ).order_by(TeamInvite.created_at.desc())
    )
    invites = result.scalars().all()

    return {
        "invites": [
            {
                "id": str(inv.id),
                "email": inv.email,
                "role": inv.role,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in invites
        ]
    }


@router.delete("/invites/{invite_id}", status_code=status.HTTP_200_OK)
async def revoke_invite(
    invite_id: str,
    user: dict = Depends(require_role("owner", "office_manager")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke a pending invite."""
    result = await db.execute(
        select(TeamInvite).where(
            TeamInvite.id == invite_id,
            TeamInvite.practice_id == user["practice_id"],
            TeamInvite.status == "pending",
        )
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")

    invite.status = "revoked"

    await audit_log(
        db,
        practice_id=user["practice_id"],
        user_id=user["user_id"],
        action="team.revoke_invite",
        resource_type="team_invite",
        resource_id=invite_id,
        details=f"Revoked invite for {invite.email}",
    )
    await db.commit()

    logger.info("Invite revoked for %s in practice %s", invite.email, user["practice_id"])

    return {"message": "Invite revoked", "invite_id": invite_id}
