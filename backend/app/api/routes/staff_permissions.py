"""OrthoFlow — Staff Permissions API routes.

Provides endpoints to view/update per-user permissions.
Only accessible by Owner, Doctor, and Office Manager roles.
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import User as UserModel
from app.models.permissions import (
    UserPermission,
    PERMISSION_KEYS,
    PERMISSION_CATEGORIES,
    ROLE_TEMPLATES,
)

router = APIRouter(prefix="/api/v1/staff-permissions", tags=["staff-permissions"])

# ── Auth Helper ───────────────────────────────────────────────────────────────

ALLOWED_ROLES = {"owner", "doctor", "office_manager"}


async def _require_permission_access(user: dict, db: AsyncSession) -> None:
    """Only Owner, Doctor, or Office Manager can manage permissions."""
    staff_result = await db.execute(
        select(UserModel).where(UserModel.id == uuid.UUID(user["user_id"]))
    )
    staff = staff_result.scalar_one_or_none()
    if not staff or staff.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner, Doctor, or Office Manager can manage permissions",
        )


# ── Schemas ───────────────────────────────────────────────────────────────────


class PermissionUpdate(BaseModel):
    user_id: str = Field(..., min_length=1)
    permission_key: str = Field(..., min_length=1)
    granted: bool


class BulkPermissionUpdate(BaseModel):
    user_id: str = Field(..., min_length=1)
    permissions: dict[str, bool]  # key -> granted


class ApplyTemplateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    role_template: str = Field(..., min_length=1)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/schema")
async def get_permission_schema(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the full permission schema (categories, keys, role templates)."""
    await _require_permission_access(user, db)

    return {
        "categories": PERMISSION_CATEGORIES,
        "permissions": PERMISSION_KEYS,
        "role_templates": ROLE_TEMPLATES,
    }


@router.get("/staff")
async def get_staff_permissions(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get all staff members with their current effective permissions."""
    await _require_permission_access(user, db)
    practice_id = uuid.UUID(user["practice_id"])

    # Get all staff members
    staff_result = await db.execute(
        select(UserModel)
        .where(UserModel.practice_id == practice_id, UserModel.is_active == True)
        .order_by(UserModel.full_name)
    )
    staff_members = staff_result.scalars().all()

    # Get all permission overrides for this practice
    perms_result = await db.execute(
        select(UserPermission).where(UserPermission.practice_id == practice_id)
    )
    all_overrides = perms_result.scalars().all()

    # Build override lookup: user_id -> {key: granted}
    override_map: dict[str, dict[str, bool]] = {}
    for perm in all_overrides:
        uid = str(perm.user_id)
        if uid not in override_map:
            override_map[uid] = {}
        override_map[uid][perm.permission_key] = perm.granted

    # Build response
    staff_list = []
    for member in staff_members:
        uid = str(member.id)
        role = member.role or "front_desk"
        template_perms = ROLE_TEMPLATES.get(role, [])
        overrides = override_map.get(uid, {})

        # Effective permissions: start from template, apply overrides
        effective: dict[str, bool] = {}
        for key in PERMISSION_KEYS:
            if key in overrides:
                effective[key] = overrides[key]
            else:
                effective[key] = key in template_perms

        staff_list.append({
            "id": uid,
            "full_name": member.full_name,
            "email": member.email,
            "role": role,
            "permissions": effective,
            "has_overrides": len(overrides) > 0,
        })

    return {"staff": staff_list}


@router.patch("/update")
async def update_permission(
    body: PermissionUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update a single permission for a user."""
    await _require_permission_access(user, db)
    practice_id = uuid.UUID(user["practice_id"])
    target_user_id = uuid.UUID(body.user_id)

    if body.permission_key not in PERMISSION_KEYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid permission key")

    # Upsert permission override
    existing = await db.execute(
        select(UserPermission).where(
            UserPermission.user_id == target_user_id,
            UserPermission.permission_key == body.permission_key,
            UserPermission.practice_id == practice_id,
        )
    )
    perm = existing.scalar_one_or_none()

    if perm:
        perm.granted = body.granted
        perm.updated_by = uuid.UUID(user["user_id"])
    else:
        perm = UserPermission(
            practice_id=practice_id,
            user_id=target_user_id,
            permission_key=body.permission_key,
            granted=body.granted,
            updated_by=uuid.UUID(user["user_id"]),
        )
        db.add(perm)

    await db.commit()
    return {"status": "updated"}


@router.patch("/bulk-update")
async def bulk_update_permissions(
    body: BulkPermissionUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update multiple permissions for a user at once."""
    await _require_permission_access(user, db)
    practice_id = uuid.UUID(user["practice_id"])
    target_user_id = uuid.UUID(body.user_id)

    for key, granted in body.permissions.items():
        if key not in PERMISSION_KEYS:
            continue

        existing = await db.execute(
            select(UserPermission).where(
                UserPermission.user_id == target_user_id,
                UserPermission.permission_key == key,
                UserPermission.practice_id == practice_id,
            )
        )
        perm = existing.scalar_one_or_none()

        if perm:
            perm.granted = granted
            perm.updated_by = uuid.UUID(user["user_id"])
        else:
            perm = UserPermission(
                practice_id=practice_id,
                user_id=target_user_id,
                permission_key=key,
                granted=granted,
                updated_by=uuid.UUID(user["user_id"]),
            )
            db.add(perm)

    await db.commit()
    return {"status": "updated"}


@router.post("/apply-template")
async def apply_role_template(
    body: ApplyTemplateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Apply a role template to a user, resetting all overrides."""
    await _require_permission_access(user, db)
    practice_id = uuid.UUID(user["practice_id"])
    target_user_id = uuid.UUID(body.user_id)

    if body.role_template not in ROLE_TEMPLATES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role template")

    # Delete all existing overrides for this user
    await db.execute(
        delete(UserPermission).where(
            UserPermission.user_id == target_user_id,
            UserPermission.practice_id == practice_id,
        )
    )

    await db.commit()
    return {"status": "template_applied", "role": body.role_template}
