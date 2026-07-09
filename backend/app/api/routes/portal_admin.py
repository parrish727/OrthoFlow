"""OrthoFlow API — Patient Portal Administration (Staff-Facing).

Staff endpoints for managing portal accounts, patient messaging, form submissions,
and form templates. All endpoints use staff JWT (get_current_user).
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.models.portal import PortalAccount, PortalForm, PortalFormSubmission, PortalMessage
from app.models.clinical import Patient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/portal/admin", tags=["portal-admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class AccountPatch(BaseModel):
    is_active: bool


class StaffMessageCreate(BaseModel):
    subject: str | None = Field(None, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)


class FormCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    form_type: str = Field(..., pattern="^(intake|consent|health_history|financial|other)$")
    description: str | None = Field(None, max_length=500)
    fields: list[dict] = Field(..., min_length=1, description="Array of field definitions")
    is_required_new_patient: bool = False


class FormUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    fields: list[dict] | None = None
    is_active: bool | None = None
    is_required_new_patient: bool | None = None


# ── Portal Accounts ───────────────────────────────────────────────────────────


@router.get("/accounts")
async def list_portal_accounts(
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search by email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all patient portal accounts for the practice."""
    practice_id = user["practice_id"]

    query = select(PortalAccount).where(PortalAccount.practice_id == practice_id)
    if is_active is not None:
        query = query.where(PortalAccount.is_active == is_active)
    if search:
        query = query.where(PortalAccount.email.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = query.order_by(PortalAccount.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    accounts = result.scalars().all()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="portal_account.list",
        resource_type="portal_account",
    )

    return {
        "total": total,
        "accounts": [
            {
                "id": str(a.id),
                "patient_id": str(a.patient_id),
                "email": a.email,
                "is_active": a.is_active,
                "is_verified": a.is_verified,
                "last_login": a.last_login.isoformat() if a.last_login else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in accounts
        ],
    }


@router.post("/invite/{patient_id}", status_code=status.HTTP_201_CREATED)
async def invite_patient(
    patient_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate an invite token for a patient to register on the portal."""
    practice_id = user["practice_id"]

    # Verify patient exists in practice
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.practice_id == practice_id,
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Check if portal account already exists
    existing_result = await db.execute(
        select(PortalAccount).where(PortalAccount.patient_id == patient_id)
    )
    existing = existing_result.scalar_one_or_none()

    invite_token = secrets.token_urlsafe(32)

    if existing:
        # Re-issue invite for existing unverified account, or re-activate
        if existing.is_verified and existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Patient already has an active portal account",
            )
        existing.verification_token = invite_token
        existing.is_verified = False
        existing.updated_at = datetime.now(timezone.utc)
        account_id = str(existing.id)
    else:
        # Create new pending portal account
        account = PortalAccount(
            practice_id=practice_id,
            patient_id=patient_id,
            email="",
            password_hash="",
            is_active=True,
            is_verified=False,
            verification_token=invite_token,
        )
        db.add(account)
        await db.flush()
        account_id = str(account.id)

    await db.commit()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="portal_account.invite",
        resource_type="portal_account",
        resource_id=account_id,
        details=f"Invite generated for patient {patient_id}",
    )

    logger.info("Portal invite generated: account=%s patient=%s", account_id, patient_id)
    return {
        "account_id": account_id,
        "patient_id": patient_id,
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "invite_token": invite_token,
        "expires": "No expiry — token invalidated on use",
    }


@router.patch("/accounts/{account_id}")
async def update_portal_account(
    account_id: str,
    payload: AccountPatch,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Activate or deactivate a patient portal account."""
    practice_id = user["practice_id"]

    result = await db.execute(
        select(PortalAccount).where(
            PortalAccount.id == account_id,
            PortalAccount.practice_id == practice_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portal account not found")

    account.is_active = payload.is_active
    account.updated_at = datetime.now(timezone.utc)
    await db.commit()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="portal_account.update",
        resource_type="portal_account",
        resource_id=account_id,
        details=f"is_active set to {payload.is_active}",
    )

    return {
        "id": str(account.id),
        "patient_id": str(account.patient_id),
        "is_active": account.is_active,
    }


# ── Portal Messages (Staff) ───────────────────────────────────────────────────


@router.get("/messages")
async def list_all_messages(
    unread_only: bool = Query(False, description="Show only unread messages from patients"),
    patient_id: str | None = Query(None, description="Filter by patient"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all portal messages for staff to review and respond."""
    practice_id = user["practice_id"]

    query = select(PortalMessage).where(PortalMessage.practice_id == practice_id)

    if unread_only:
        query = query.where(
            PortalMessage.direction == "from_patient",
            PortalMessage.is_read == False,  # noqa: E712
        )
    if patient_id:
        query = query.where(PortalMessage.patient_id == patient_id)

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = query.order_by(PortalMessage.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    messages = result.scalars().all()

    return {
        "total": total,
        "messages": [
            {
                "id": str(m.id),
                "patient_id": str(m.patient_id),
                "direction": m.direction,
                "subject": m.subject,
                "body": m.body,
                "is_read": m.is_read,
                "read_at": m.read_at.isoformat() if m.read_at else None,
                "sent_by_staff": str(m.sent_by_staff) if m.sent_by_staff else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/messages/{patient_id}", status_code=status.HTTP_201_CREATED)
async def send_staff_message(
    patient_id: str,
    payload: StaffMessageCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Staff sends a message to a patient via the portal."""
    practice_id = user["practice_id"]

    # Verify patient has an active portal account
    account_result = await db.execute(
        select(PortalAccount).where(
            PortalAccount.patient_id == patient_id,
            PortalAccount.practice_id == practice_id,
            PortalAccount.is_active == True,  # noqa: E712
            PortalAccount.is_verified == True,  # noqa: E712
        )
    )
    if not account_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active portal account found for this patient",
        )

    message = PortalMessage(
        practice_id=practice_id,
        patient_id=patient_id,
        direction="to_patient",
        subject=payload.subject,
        body=payload.body,
        is_read=False,
        sent_by_staff=user["user_id"],
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="portal_message.staff_send",
        resource_type="portal_message",
        resource_id=str(message.id),
        details=f"Staff message to patient {patient_id}",
    )

    logger.info("Staff message sent: message=%s to patient=%s", str(message.id), patient_id)
    return {"id": str(message.id), "created_at": message.created_at.isoformat()}


@router.patch("/messages/{message_id}/read")
async def mark_message_read(
    message_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a patient message as read."""
    practice_id = user["practice_id"]

    result = await db.execute(
        select(PortalMessage).where(
            PortalMessage.id == message_id,
            PortalMessage.practice_id == practice_id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.now(timezone.utc)
        await db.commit()

    return {
        "id": str(message.id),
        "is_read": message.is_read,
        "read_at": message.read_at.isoformat() if message.read_at else None,
    }


# ── Form Submissions ──────────────────────────────────────────────────────────


@router.get("/submissions")
async def list_form_submissions(
    status_filter: str | None = Query(None, alias="status", pattern="^(submitted|reviewed)$"),
    form_id: str | None = Query(None, description="Filter by form ID"),
    patient_id: str | None = Query(None, description="Filter by patient"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List form submissions for staff to review."""
    practice_id = user["practice_id"]

    query = select(PortalFormSubmission).where(
        PortalFormSubmission.practice_id == practice_id,
    )
    if status_filter:
        query = query.where(PortalFormSubmission.status == status_filter)
    if form_id:
        query = query.where(PortalFormSubmission.form_id == form_id)
    if patient_id:
        query = query.where(PortalFormSubmission.patient_id == patient_id)

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = query.order_by(PortalFormSubmission.submitted_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    submissions = result.scalars().all()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="portal_form_submission.list",
        resource_type="portal_form_submission",
    )

    return {
        "total": total,
        "submissions": [
            {
                "id": str(s.id),
                "patient_id": str(s.patient_id),
                "form_id": str(s.form_id),
                "status": s.status,
                "responses": s.responses,
                "reviewed_by": str(s.reviewed_by) if s.reviewed_by else None,
                "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
                "submitted_at": s.submitted_at.isoformat(),
            }
            for s in submissions
        ],
    }


@router.patch("/submissions/{submission_id}/review")
async def review_form_submission(
    submission_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a form submission as reviewed by staff."""
    practice_id = user["practice_id"]

    result = await db.execute(
        select(PortalFormSubmission).where(
            PortalFormSubmission.id == submission_id,
            PortalFormSubmission.practice_id == practice_id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    if submission.status == "reviewed":
        return {
            "id": str(submission.id),
            "status": "reviewed",
            "reviewed_at": submission.reviewed_at.isoformat() if submission.reviewed_at else None,
        }

    submission.status = "reviewed"
    submission.reviewed_by = user["user_id"]
    submission.reviewed_at = datetime.now(timezone.utc)
    await db.commit()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="portal_form_submission.review",
        resource_type="portal_form_submission",
        resource_id=submission_id,
    )

    return {
        "id": str(submission.id),
        "status": submission.status,
        "reviewed_by": str(submission.reviewed_by),
        "reviewed_at": submission.reviewed_at.isoformat(),
    }


# ── Form Management ───────────────────────────────────────────────────────────


@router.get("/forms")
async def list_forms(
    include_inactive: bool = Query(False),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List practice forms (active and optionally inactive)."""
    practice_id = user["practice_id"]

    query = select(PortalForm).where(PortalForm.practice_id == practice_id)
    if not include_inactive:
        query = query.where(PortalForm.is_active == True)  # noqa: E712
    query = query.order_by(PortalForm.name)

    result = await db.execute(query)
    forms = result.scalars().all()

    return {
        "forms": [
            {
                "id": str(f.id),
                "name": f.name,
                "form_type": f.form_type,
                "description": f.description,
                "fields": f.fields,
                "is_active": f.is_active,
                "is_required_new_patient": f.is_required_new_patient,
                "version": f.version,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat(),
            }
            for f in forms
        ],
    }


@router.post("/forms", status_code=status.HTTP_201_CREATED)
async def create_form(
    payload: FormCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new patient portal form."""
    practice_id = user["practice_id"]

    form = PortalForm(
        practice_id=practice_id,
        name=payload.name,
        form_type=payload.form_type,
        description=payload.description,
        fields=payload.fields,
        is_active=True,
        is_required_new_patient=payload.is_required_new_patient,
        version=1,
    )
    db.add(form)
    await db.commit()
    await db.refresh(form)

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="portal_form.create",
        resource_type="portal_form",
        resource_id=str(form.id),
        details=f"Created form: {payload.name}",
    )

    logger.info("Portal form created: %s in practice %s", str(form.id), practice_id)
    return {
        "id": str(form.id),
        "name": form.name,
        "form_type": form.form_type,
        "version": form.version,
        "created_at": form.created_at.isoformat(),
    }


@router.patch("/forms/{form_id}")
async def update_form(
    form_id: str,
    payload: FormUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a portal form. Updating fields increments the version."""
    practice_id = user["practice_id"]

    result = await db.execute(
        select(PortalForm).where(
            PortalForm.id == form_id,
            PortalForm.practice_id == practice_id,
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")

    if payload.name is not None:
        form.name = payload.name
    if payload.description is not None:
        form.description = payload.description
    if payload.is_active is not None:
        form.is_active = payload.is_active
    if payload.is_required_new_patient is not None:
        form.is_required_new_patient = payload.is_required_new_patient
    if payload.fields is not None:
        form.fields = payload.fields
        form.version += 1  # Increment version when fields change

    form.updated_at = datetime.now(timezone.utc)
    await db.commit()

    await audit_log(
        db,
        practice_id=practice_id,
        user_id=user["user_id"],
        action="portal_form.update",
        resource_type="portal_form",
        resource_id=form_id,
        details=f"Updated form: {form.name} to version {form.version}",
    )

    return {
        "id": str(form.id),
        "name": form.name,
        "form_type": form.form_type,
        "is_active": form.is_active,
        "version": form.version,
        "updated_at": form.updated_at.isoformat(),
    }
