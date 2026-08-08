"""OrthoFlow API — Invisalign Case Management.
Tracks clear aligner cases from ClinCheck through completion.
Connected to doctor's Invisalign provider account.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/v1/invisalign", tags=["invisalign"])

VALID_STATUSES = [
    "clincheck_submitted", "clincheck_review", "clincheck_approved",
    "aligners_ordered", "aligners_received", "in_treatment",
    "refinement", "complete",
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    patient_id: str
    patient_name: str = ""
    case_number: str = Field(..., min_length=1, max_length=50)
    total_stages: int = Field(20, ge=1, le=100)
    upper_aligners: int = Field(20, ge=0)
    lower_aligners: int = Field(20, ge=0)
    ipr_planned: bool = False
    notes: str | None = None


class StatusUpdate(BaseModel):
    status: str


# ── In-memory store (demo mode — production would use DB table) ───────────────

_cases: dict[str, dict[str, Any]] = {}
_settings: dict[str, dict[str, Any]] = {
    "82fe9d87-6250-4b15-ac7d-26de094a4be8": {
        "provider_id": "DR-PKN-2024",
        "provider_name": "Dr. Parrish Knowles",
        "practice_name": "Brightsmile Orthodontics",
        "tier": "Gold",
        "cases_this_year": 18,
    }
}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/cases")
async def list_cases(
    user: dict = Depends(get_current_user),
) -> dict:
    """List all Invisalign cases for the practice."""
    practice_id = user["practice_id"]
    cases = [c for c in _cases.values() if c["practice_id"] == practice_id]
    cases.sort(key=lambda c: c["created_at"], reverse=True)
    return {"cases": cases}


@router.post("/cases", status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new Invisalign case."""
    practice_id = user["practice_id"]

    # Look up patient name if not provided
    patient_name = body.patient_name
    if not patient_name:
        from app.models.clinical import Patient
        result = await db.execute(select(Patient).where(Patient.id == uuid.UUID(body.patient_id)))
        patient = result.scalar_one_or_none()
        if patient:
            patient_name = f"{patient.first_name} {patient.last_name}"

    case_id = str(uuid.uuid4())
    case = {
        "id": case_id,
        "practice_id": practice_id,
        "patient_id": body.patient_id,
        "patient_name": patient_name,
        "case_number": body.case_number,
        "status": "clincheck_submitted",
        "total_stages": body.total_stages,
        "current_stage": 0,
        "upper_aligners": body.upper_aligners,
        "lower_aligners": body.lower_aligners,
        "ipr_planned": body.ipr_planned,
        "attachments_placed": False,
        "refinement_number": 0,
        "clincheck_url": None,
        "notes": body.notes,
        "started_at": None,
        "estimated_completion": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _cases[case_id] = case
    return case


@router.patch("/cases/{case_id}/status")
async def update_case_status(
    case_id: str,
    body: StatusUpdate,
    user: dict = Depends(get_current_user),
) -> dict:
    """Update an Invisalign case status."""
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    case = _cases.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case["practice_id"] != user["practice_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    case["status"] = body.status

    # Auto-set timestamps
    if body.status == "in_treatment" and not case["started_at"]:
        case["started_at"] = datetime.now(timezone.utc).isoformat()
    if body.status == "refinement":
        case["refinement_number"] += 1

    return case


@router.get("/settings")
async def get_settings(
    user: dict = Depends(get_current_user),
) -> dict:
    """Get Invisalign provider settings for the practice."""
    practice_id = user["practice_id"]
    settings = _settings.get(practice_id)
    if not settings:
        return {"provider_id": "", "provider_name": "", "practice_name": "", "tier": "Not Connected", "cases_this_year": 0}
    return settings
