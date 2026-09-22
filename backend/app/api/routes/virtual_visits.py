"""OrthoFlow — Virtual Visits (LiveKit video) routes."""
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from livekit import api as livekit_api
except ImportError:
    livekit_api = None  # type: ignore[assignment]

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.clinical import Patient
from app.models.models import User as UserModel

router = APIRouter(prefix="/api/v1/virtual-visits")

# ── Config ────────────────────────────────────────────────────────────────────

LIVEKIT_API_KEY: str = os.environ.get("LIVEKIT_API_KEY", "APIorthoflow")
LIVEKIT_API_SECRET: str = os.environ.get("LIVEKIT_API_SECRET", "")
LIVEKIT_URL: str = os.environ.get("LIVEKIT_URL", "ws://livekit:7880")

# ── Schemas ───────────────────────────────────────────────────────────────────


class CreateVisitRequest(BaseModel):
    appointment_id: str = Field(..., min_length=1, max_length=100)
    patient_id: str = Field(..., min_length=1, max_length=100)


class VisitResponse(BaseModel):
    visit_id: str
    room_name: str
    staff_token: str
    join_url: str


class VisitDetailResponse(BaseModel):
    visit_id: str
    room_name: str
    patient_token: str
    join_url: str
    status: str
    created_at: str


class ActiveVisitResponse(BaseModel):
    visit_id: str
    room_name: str
    status: str
    created_at: str
    appointment_id: str
    patient_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _generate_token(identity: str, room_name: str, can_publish: bool = True, can_subscribe: bool = True) -> str:
    """Generate a LiveKit access token with video grants."""
    if livekit_api is None:
        # Fallback: return a placeholder token when livekit-api not installed
        return f"demo-token-{identity}-{room_name}"
    from datetime import timedelta
    token = (
        livekit_api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_grants(
            livekit_api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=can_publish,
                can_subscribe=can_subscribe,
            )
        )
        .with_ttl(timedelta(hours=4))
        .to_jwt()
    )
    return token


def _build_join_url(room_name: str, token: str) -> str:
    """Build the client-side join URL."""
    base_url = LIVEKIT_URL.replace("ws://", "http://").replace("wss://", "https://")
    return f"{base_url}/join?room={room_name}&token={token}"


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/create", response_model=VisitResponse, status_code=status.HTTP_201_CREATED)
async def create_virtual_visit(
    body: CreateVisitRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisitResponse:
    """Create a new virtual visit room and generate tokens for staff and patient."""
    # Look up staff email
    staff_result = await db.execute(
        select(UserModel).where(UserModel.id == uuid.UUID(user["user_id"]))
    )
    staff_user = staff_result.scalar_one_or_none()
    if not staff_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found")

    # Look up patient name
    patient_result = await db.execute(
        select(Patient).where(
            Patient.id == uuid.UUID(body.patient_id),
            Patient.practice_id == uuid.UUID(user["practice_id"]),
        )
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    room_name = f"visit-{body.appointment_id}"
    patient_name = f"{patient.first_name} {patient.last_name}"

    # Generate tokens
    staff_token = _generate_token(identity=staff_user.email, room_name=room_name)
    patient_token = _generate_token(identity=patient_name, room_name=room_name)

    # Create LiveKit room
    try:
        if livekit_api is not None:
            lkapi = livekit_api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            await lkapi.room.create_room(livekit_api.CreateRoomRequest(name=room_name))
            await lkapi.aclose()
    except Exception:
        # Room creation is best-effort — LiveKit auto-creates on first join
        pass

    # Store visit record
    visit_id = str(uuid.uuid4())
    _visits[visit_id] = {
        "visit_id": visit_id,
        "room_name": room_name,
        "staff_token": staff_token,
        "patient_token": patient_token,
        "status": "active",
        "appointment_id": body.appointment_id,
        "patient_id": body.patient_id,
        "practice_id": user["practice_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    join_url = _build_join_url(room_name, staff_token)

    # Persist the visit (idempotent: reuse a still-open visit for the same appointment so a
    # doctor clicking "start" twice doesn't create duplicate rooms/rows).
    from app.models.portal import VirtualVisit, AppointmentNotification
    appt_uuid = uuid.UUID(body.appointment_id) if _is_uuid(body.appointment_id) else None
    existing = None
    if appt_uuid is not None:
        existing = (await db.execute(
            select(VirtualVisit).where(
                VirtualVisit.practice_id == uuid.UUID(user["practice_id"]),
                VirtualVisit.appointment_id == appt_uuid,
                VirtualVisit.status != "ended",
            ).limit(1)
        )).scalar_one_or_none()

    if existing is not None:
        visit = existing
    else:
        visit = VirtualVisit(
            practice_id=uuid.UUID(user["practice_id"]),
            patient_id=uuid.UUID(body.patient_id),
            appointment_id=appt_uuid,
            room_name=room_name,
            staff_token=staff_token,
            patient_token=patient_token,
            status="waiting",
            created_by=uuid.UUID(user["user_id"]),
        )
        db.add(visit)
        await db.flush()
        # Notify the patient (MyOrthoChart) that the doctor opened the visit — deduped by the
        # notification helper analog (only on first creation). One-way: only staff creates.
        db.add(AppointmentNotification(
            practice_id=visit.practice_id, patient_id=visit.patient_id,
            appointment_id=appt_uuid, audience="patient", kind="virtual_visit_ready",
            title="Your doctor is ready — join your virtual visit",
            body="Tap to join your video visit now.", action_url="/portal",
        ))
    await db.commit()
    await db.refresh(visit)

    join_url = _build_join_url(room_name, visit.staff_token)
    return VisitResponse(
        visit_id=str(visit.id),
        room_name=visit.room_name,
        staff_token=visit.staff_token,
        join_url=join_url,
    )


@router.get("/active", response_model=list[ActiveVisitResponse])
async def get_active_visits(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ActiveVisitResponse]:
    """Get all currently open (waiting/live) virtual visits for the practice."""
    from app.models.portal import VirtualVisit
    rows = (await db.execute(
        select(VirtualVisit).where(
            VirtualVisit.practice_id == uuid.UUID(user["practice_id"]),
            VirtualVisit.status != "ended",
        ).order_by(VirtualVisit.created_at.desc())
    )).scalars().all()
    return [
        ActiveVisitResponse(
            visit_id=str(v.id), room_name=v.room_name, status=v.status,
            created_at=v.created_at.isoformat() if v.created_at else "",
            appointment_id=str(v.appointment_id) if v.appointment_id else "",
            patient_id=str(v.patient_id),
        )
        for v in rows
    ]


@router.get("/{visit_id}", response_model=VisitDetailResponse)
async def get_virtual_visit(
    visit_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VisitDetailResponse:
    """Get visit details including patient join token (used by MyOrthoChart)."""
    from app.models.portal import VirtualVisit
    visit = (await db.execute(
        select(VirtualVisit).where(VirtualVisit.id == uuid.UUID(visit_id))
    )).scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if str(visit.practice_id) != str(user["practice_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    join_url = _build_join_url(visit.room_name, visit.patient_token)
    return VisitDetailResponse(
        visit_id=str(visit.id), room_name=visit.room_name, patient_token=visit.patient_token,
        join_url=join_url, status=visit.status,
        created_at=visit.created_at.isoformat() if visit.created_at else "",
    )


@router.patch("/{visit_id}/end", status_code=status.HTTP_200_OK)
async def end_virtual_visit(
    visit_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """End a virtual visit (idempotent) and delete the LiveKit room. Syncs 'ended' to the patient."""
    from app.models.portal import VirtualVisit
    visit = (await db.execute(
        select(VirtualVisit).where(VirtualVisit.id == uuid.UUID(visit_id))
    )).scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if str(visit.practice_id) != str(user["practice_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if visit.status == "ended":
        return {"status": "ended", "visit_id": visit_id}  # idempotent
    try:
        if livekit_api is not None:
            lkapi = livekit_api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            await lkapi.room.delete_room(livekit_api.DeleteRoomRequest(room=visit.room_name))
            await lkapi.aclose()
    except Exception:
        pass  # Best-effort cleanup
    visit.status = "ended"
    visit.ended_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "ended", "visit_id": visit_id}
