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

# ── In-Memory Store (temporary — DB model to follow) ──────────────────────────

_visits: dict[str, dict[str, Any]] = {}

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

    return VisitResponse(
        visit_id=visit_id,
        room_name=room_name,
        staff_token=staff_token,
        join_url=join_url,
    )


@router.get("/active", response_model=list[ActiveVisitResponse])
async def get_active_visits(
    user: dict = Depends(get_current_user),
) -> list[ActiveVisitResponse]:
    """Get all currently active virtual visits for the practice."""
    active = [
        ActiveVisitResponse(
            visit_id=v["visit_id"],
            room_name=v["room_name"],
            status=v["status"],
            created_at=v["created_at"],
            appointment_id=v["appointment_id"],
            patient_id=v["patient_id"],
        )
        for v in _visits.values()
        if v["practice_id"] == user["practice_id"] and v["status"] == "active"
    ]
    return active


@router.get("/{visit_id}", response_model=VisitDetailResponse)
async def get_virtual_visit(
    visit_id: str,
    user: dict = Depends(get_current_user),
) -> VisitDetailResponse:
    """Get visit details including patient join token (used by MyOrthoChart)."""
    visit = _visits.get(visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    if visit["practice_id"] != user["practice_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    join_url = _build_join_url(visit["room_name"], visit["patient_token"])

    return VisitDetailResponse(
        visit_id=visit["visit_id"],
        room_name=visit["room_name"],
        patient_token=visit["patient_token"],
        join_url=join_url,
        status=visit["status"],
        created_at=visit["created_at"],
    )


@router.patch("/{visit_id}/end", status_code=status.HTTP_200_OK)
async def end_virtual_visit(
    visit_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """End a virtual visit and delete the LiveKit room."""
    visit = _visits.get(visit_id)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    if visit["practice_id"] != user["practice_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if visit["status"] != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visit already ended")

    # Delete LiveKit room
    try:
        if livekit_api is not None:
            lkapi = livekit_api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            await lkapi.room.delete_room(livekit_api.DeleteRoomRequest(room=visit["room_name"]))
            await lkapi.aclose()
    except Exception:
        pass  # Best-effort cleanup

    visit["status"] = "ended"
    visit["ended_at"] = datetime.now(timezone.utc).isoformat()

    return {"status": "ended", "visit_id": visit_id}
