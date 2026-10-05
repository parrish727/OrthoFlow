"""OrthoFlow API — Cephalometric Tracing (Ceph Suite Phase A).

Endpoints for the tracing editor: list analyses (built-in + custom), create/get/update a tracing,
recompute measurements from landmarks, set/refine calibration, and finalize (doctor sign-off).
All practice-scoped via JWT. AI-assisted tracings (Phase B) are drafts; finalize requires a user.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.ceph import CephTracing, CephAnalysisDefinition
from app.models.imaging import PatientImage
from app.services import ceph_engine

router = APIRouter(prefix="/api/v1/ceph", tags=["ceph"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class Calibration(BaseModel):
    px_per_mm: float = Field(..., gt=0)
    method: str = Field("known_distance", max_length=30)  # known_distance|ruler|dpi
    ref_mm: float | None = None
    ref_px: float | None = None


class TracingCreate(BaseModel):
    image_id: str
    analysis_type: str = Field("abo", max_length=40)
    landmarks: dict = Field(default_factory=dict)
    calibration: Calibration | None = None
    is_ai_assisted: bool = False


class TracingUpdate(BaseModel):
    landmarks: dict | None = None
    analysis_type: str | None = Field(None, max_length=40)
    calibration: Calibration | None = None
    notes: str | None = None


def _measurement_keys_for(db_analysis: CephAnalysisDefinition | None, analysis_type: str) -> list[str]:
    if db_analysis and db_analysis.measurement_keys:
        return list(db_analysis.measurement_keys)
    return ceph_engine.analysis_measurements(analysis_type)


async def _resolve_analysis(db, practice_id, key: str) -> CephAnalysisDefinition | None:
    return (await db.execute(
        select(CephAnalysisDefinition).where(
            CephAnalysisDefinition.key == key,
            or_(CephAnalysisDefinition.practice_id == practice_id,
                CephAnalysisDefinition.practice_id.is_(None)),
            CephAnalysisDefinition.is_active == True,  # noqa: E712
        ).order_by(CephAnalysisDefinition.practice_id.isnot(None).desc()).limit(1)
    )).scalar_one_or_none()


def _tracing_dict(t: CephTracing) -> dict:
    return {
        "id": str(t.id),
        "patient_id": str(t.patient_id),
        "image_id": str(t.image_id),
        "analysis_type": t.analysis_type,
        "landmarks": t.landmarks or {},
        "measurements": t.measurements or {},
        "calibration": t.calibration,
        "status": t.status,
        "is_ai_assisted": t.is_ai_assisted,
        "ai_confidence": t.ai_confidence,
        "notes": t.notes,
        "finalized_at": t.finalized_at.isoformat() if t.finalized_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


async def _recompute(db, practice_id, t: CephTracing) -> None:
    analysis = await _resolve_analysis(db, practice_id, t.analysis_type)
    mkeys = _measurement_keys_for(analysis, t.analysis_type)
    ppm = (t.calibration or {}).get("px_per_mm") if t.calibration else None
    t.measurements = ceph_engine.compute(t.landmarks or {}, mkeys, ppm)


# ── Analyses ──────────────────────────────────────────────────────────────────

@router.get("/analyses")
async def list_analyses(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List available analyses (global built-ins + this practice's custom) with their landmark +
    measurement sets, so the editor knows which points to prompt for."""
    practice_id = uuid.UUID(user["practice_id"])
    rows = (await db.execute(
        select(CephAnalysisDefinition).where(
            or_(CephAnalysisDefinition.practice_id == practice_id,
                CephAnalysisDefinition.practice_id.is_(None)),
            CephAnalysisDefinition.is_active == True,  # noqa: E712
        )
    )).scalars().all()
    if not rows:
        # Fallback to the engine's built-in registry if definitions haven't been seeded yet.
        return {"analyses": [
            {"key": k, "name": v[0], "description": v[1], "landmark_keys": list(v[2]),
             "measurement_keys": list(v[3]), "is_builtin": True}
            for k, v in ceph_engine.ANALYSES.items()
        ]}
    return {"analyses": [
        {"key": r.key, "name": r.name, "description": r.description,
         "landmark_keys": r.landmark_keys, "measurement_keys": r.measurement_keys,
         "is_builtin": r.is_builtin}
        for r in rows
    ]}


# ── Tracings ──────────────────────────────────────────────────────────────────

@router.post("/tracings", status_code=status.HTTP_201_CREATED)
async def create_tracing(body: TracingCreate, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    practice_id = uuid.UUID(user["practice_id"])
    image = (await db.execute(
        select(PatientImage).where(PatientImage.id == uuid.UUID(body.image_id), PatientImage.practice_id == practice_id)
    )).scalar_one_or_none()
    if not image:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")

    t = CephTracing(
        id=uuid.uuid4(), practice_id=practice_id, patient_id=image.patient_id, image_id=image.id,
        analysis_type=body.analysis_type, landmarks=body.landmarks or {},
        calibration=body.calibration.model_dump() if body.calibration else None,
        is_ai_assisted=body.is_ai_assisted, status="draft",
        traced_by=uuid.UUID(user["user_id"]) if user.get("user_id") else None,
    )
    await _recompute(db, practice_id, t)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    await audit_log(db, user["practice_id"], user["user_id"], "ceph.tracing_create", "ceph_tracings", str(t.id))
    return _tracing_dict(t)


@router.get("/tracings/{tracing_id}")
async def get_tracing(tracing_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = await _get_owned(db, user, tracing_id)
    return _tracing_dict(t)


@router.get("/patients/{patient_id}/tracings")
async def list_patient_tracings(patient_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    practice_id = uuid.UUID(user["practice_id"])
    rows = (await db.execute(
        select(CephTracing).where(
            CephTracing.patient_id == uuid.UUID(patient_id),
            CephTracing.practice_id == practice_id,
        ).order_by(CephTracing.created_at.desc())
    )).scalars().all()
    return {"tracings": [_tracing_dict(t) for t in rows]}


@router.patch("/tracings/{tracing_id}")
async def update_tracing(tracing_id: str, body: TracingUpdate, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    practice_id = uuid.UUID(user["practice_id"])
    t = await _get_owned(db, user, tracing_id)
    if t.status == "finalized":
        raise HTTPException(status.HTTP_409_CONFLICT, "Tracing is finalized; create a new tracing to make changes")
    if body.landmarks is not None:
        t.landmarks = body.landmarks
    if body.analysis_type is not None:
        t.analysis_type = body.analysis_type
    if body.calibration is not None:
        t.calibration = body.calibration.model_dump()
    if body.notes is not None:
        t.notes = body.notes
    await _recompute(db, practice_id, t)  # dynamic refinement: measurements recompute live
    await db.commit()
    await db.refresh(t)
    return _tracing_dict(t)


@router.post("/tracings/{tracing_id}/finalize")
async def finalize_tracing(tracing_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Doctor sign-off. Required before a tracing is used in reports/superimposition. No AI
    auto-finalize — a user must explicitly finalize."""
    t = await _get_owned(db, user, tracing_id)
    t.status = "finalized"
    t.finalized_by = uuid.UUID(user["user_id"]) if user.get("user_id") else None
    t.finalized_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(t)
    await audit_log(db, user["practice_id"], user["user_id"], "ceph.tracing_finalize", "ceph_tracings", str(t.id))
    return _tracing_dict(t)


async def _get_owned(db, user, tracing_id: str) -> CephTracing:
    t = (await db.execute(
        select(CephTracing).where(
            CephTracing.id == uuid.UUID(tracing_id),
            CephTracing.practice_id == uuid.UUID(user["practice_id"]),
        )
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tracing not found")
    return t
