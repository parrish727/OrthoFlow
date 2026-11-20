from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.core.audit import audit_log
from app.services.storage import upload_file

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
        "ar_auto_outreach_enabled": practice.ar_auto_outreach_enabled,
    }


class AROutreachSetting(BaseModel):
    enabled: bool


@router.get("/me/ar-outreach")
async def get_ar_outreach(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Whether automatic collections reminders (30/60/90/120/180 days past due) are on."""
    from app.models.models import Practice
    from app.services import ar_aging
    practice = (await db.execute(select(Practice).where(Practice.id == current_user["practice_id"]))).scalar_one_or_none()
    return {
        "enabled": bool(practice and practice.ar_auto_outreach_enabled),
        "enabled_at": practice.ar_auto_outreach_enabled_at.isoformat() if practice and practice.ar_auto_outreach_enabled_at else None,
        "milestones": list(ar_aging.active_milestones()),
        "cap_days": ar_aging.cap_days(),
    }


@router.put("/me/ar-outreach")
async def set_ar_outreach(
    body: AROutreachSetting,
    current_user: dict = Depends(require_role("owner", "doctor")),
    db: AsyncSession = Depends(get_db),
):
    """Turn automatic reminders on or off. Owner or doctor only; recorded in the audit log.

    Normally chosen once during initial setup. Off by default. Manual follow-up tools are not
    affected. Reminders go only to patients with SMS consent (TCPA) and never outside the send window.
    """
    from app.models.models import Practice
    practice = (await db.execute(select(Practice).where(Practice.id == current_user["practice_id"]))).scalar_one_or_none()
    if not practice:
        from fastapi import HTTPException
        raise HTTPException(404, "Practice not found")
    practice.ar_auto_outreach_enabled = body.enabled
    practice.ar_auto_outreach_enabled_at = datetime.now(timezone.utc) if body.enabled else None
    practice.ar_auto_outreach_enabled_by = UUID(current_user["user_id"]) if body.enabled else None
    await db.commit()
    await audit_log(db, practice.id, current_user["user_id"],
                    "practice.ar_outreach_on" if body.enabled else "practice.ar_outreach_off", "practice", str(practice.id))
    return {"enabled": practice.ar_auto_outreach_enabled}


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a practice logo."""
    from app.models.models import Practice
    content = await file.read()
    key = f"logos/{current_user['practice_id']}/{file.filename}"
    await upload_file(key, content, file.content_type or "image/png")

    # Store the URL on the practice
    result = await db.execute(select(Practice).where(Practice.id == current_user["practice_id"]))
    practice = result.scalar_one_or_none()
    if practice:
        # For local MinIO, construct the URL; for S3, use the bucket URL
        practice.logo_url = f"/api/v1/practices/logo/serve"
        await db.commit()

    return {"status": "uploaded", "filename": file.filename}


@router.get("/logo/serve")
async def serve_logo(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Serve the practice logo."""
    from app.models.models import Practice
    from app.services.storage import get_presigned_url
    from fastapi.responses import RedirectResponse

    result = await db.execute(select(Practice).where(Practice.id == current_user["practice_id"]))
    practice = result.scalar_one_or_none()
    if not practice:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    # Find the logo in S3
    import boto3
    from app.core.config import settings
    kwargs = {"aws_access_key_id": settings.S3_ACCESS_KEY, "aws_secret_access_key": settings.S3_SECRET_KEY}
    if settings.S3_ENDPOINT:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT
    client = boto3.client("s3", **kwargs)

    prefix = f"logos/{current_user['practice_id']}/"
    resp = client.list_objects_v2(Bucket=settings.S3_BUCKET, Prefix=prefix, MaxKeys=1)
    if "Contents" not in resp:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No logo uploaded")

    key = resp["Contents"][0]["Key"]
    url = await get_presigned_url(key)
    return RedirectResponse(url)
