"""Onboarding wizard endpoints — first-time setup for practices migrating to OrthoFlow."""
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/onboarding")


# ── Enums ─────────────────────────────────────────────────────────────────────


class SourceSystem(str, Enum):
    tops_ortho = "tops_ortho"
    cloud_9 = "cloud_9"
    dolphin = "dolphin"
    ortho2 = "ortho2"
    dentrix = "dentrix"
    other = "other"


class StepStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    skipped = "skipped"


ONBOARDING_STEPS = [
    "source_system",
    "practice_info",
    "import_staff",
    "configure_roles",
    "import_patients",
    "verify",
]


# ── Schemas ───────────────────────────────────────────────────────────────────


class StartOnboardingRequest(BaseModel):
    source_system: SourceSystem


class StepUpdateRequest(BaseModel):
    status: StepStatus = Field(..., description="Mark step as 'completed' or 'skipped'")


class StaffMember(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    role: str = Field(..., min_length=1, max_length=50)


class ImportStaffRequest(BaseModel):
    staff: list[StaffMember] = Field(..., min_length=1, max_length=200)


class PatientRecord(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_id: Optional[str] = None


class ImportPatientsRequest(BaseModel):
    patients: list[PatientRecord] = Field(..., min_length=1, max_length=5000)


# ── In-Memory Store (keyed by practice_id) ───────────────────────────────────


_onboarding_state: dict[str, dict] = {}


def _get_or_create_state(practice_id: str) -> dict:
    """Get existing onboarding state or create a fresh one."""
    if practice_id not in _onboarding_state:
        _onboarding_state[practice_id] = {
            "practice_id": practice_id,
            "source_system": None,
            "started_at": None,
            "completed_at": None,
            "steps": {step: StepStatus.pending for step in ONBOARDING_STEPS},
            "imported_staff": [],
            "imported_patients_count": 0,
        }
    return _onboarding_state[practice_id]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/status")
async def get_onboarding_status(
    user: dict = Depends(get_current_user),
) -> dict:
    """Returns current onboarding progress for the practice."""
    practice_id = user["practice_id"]
    state = _get_or_create_state(practice_id)

    steps_detail = []
    for i, step_name in enumerate(ONBOARDING_STEPS):
        steps_detail.append({
            "order": i + 1,
            "name": step_name,
            "status": state["steps"][step_name],
        })

    completed_count = sum(
        1 for s in state["steps"].values()
        if s in (StepStatus.completed, StepStatus.skipped)
    )

    return {
        "practice_id": practice_id,
        "source_system": state["source_system"],
        "started_at": state["started_at"],
        "completed_at": state["completed_at"],
        "steps": steps_detail,
        "progress": {
            "total": len(ONBOARDING_STEPS),
            "completed": completed_count,
            "percent": round((completed_count / len(ONBOARDING_STEPS)) * 100),
        },
        "imported_staff_count": len(state["imported_staff"]),
        "imported_patients_count": state["imported_patients_count"],
    }


@router.post("/start", status_code=status.HTTP_200_OK)
async def start_onboarding(
    body: StartOnboardingRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Initialize onboarding — sets the source system being migrated from."""
    practice_id = user["practice_id"]
    state = _get_or_create_state(practice_id)

    state["source_system"] = body.source_system.value
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state["steps"]["source_system"] = StepStatus.completed

    logger.info(
        "Onboarding started for practice %s from %s",
        practice_id,
        body.source_system.value,
    )

    return {
        "message": "Onboarding started",
        "source_system": state["source_system"],
        "started_at": state["started_at"],
    }


@router.patch("/step/{step_name}")
async def update_step(
    step_name: str,
    body: StepUpdateRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Mark a specific onboarding step as completed or skipped."""
    if step_name not in ONBOARDING_STEPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid step name. Must be one of: {ONBOARDING_STEPS}",
        )

    if body.status == StepStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot set status back to pending. Use 'completed' or 'skipped'.",
        )

    practice_id = user["practice_id"]
    state = _get_or_create_state(practice_id)
    state["steps"][step_name] = body.status

    # Check if all steps are done
    all_done = all(
        s in (StepStatus.completed, StepStatus.skipped)
        for s in state["steps"].values()
    )
    if all_done and state["completed_at"] is None:
        state["completed_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "step": step_name,
        "status": body.status,
        "all_complete": all_done,
    }


@router.post("/import-staff", status_code=status.HTTP_200_OK)
async def import_staff(
    body: ImportStaffRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Import staff list from JSON array."""
    practice_id = user["practice_id"]
    state = _get_or_create_state(practice_id)

    imported = []
    for member in body.staff:
        imported.append({
            "name": member.name,
            "email": member.email,
            "role": member.role,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        })

    state["imported_staff"] = imported
    state["steps"]["import_staff"] = StepStatus.completed

    logger.info(
        "Imported %d staff members for practice %s",
        len(imported),
        practice_id,
    )

    return {
        "message": f"Successfully imported {len(imported)} staff members",
        "count": len(imported),
        "staff": imported,
    }


@router.post("/import-patients", status_code=status.HTTP_200_OK)
async def import_patients(
    body: ImportPatientsRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Import patient list from JSON array."""
    practice_id = user["practice_id"]
    state = _get_or_create_state(practice_id)

    count = len(body.patients)
    state["imported_patients_count"] = count
    state["steps"]["import_patients"] = StepStatus.completed

    logger.info(
        "Imported %d patients for practice %s",
        count,
        practice_id,
    )

    return {
        "message": f"Successfully imported {count} patients",
        "count": count,
    }
