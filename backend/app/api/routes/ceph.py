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


class AutoLandmarkRequest(BaseModel):
    image_id: str
    analysis_type: str = Field("abo", max_length=40)


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


@router.post("/tracings/auto-landmark", status_code=status.HTTP_201_CREATED)
async def auto_landmark_tracing(body: "AutoLandmarkRequest", user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """AI-assisted auto-landmarking (Phase B). Runs the vision model on the ceph image to propose
    landmarks for the chosen analysis, then creates a DRAFT tracing (is_ai_assisted=True) with
    per-point confidence for the doctor to review and correct. Never auto-finalized. Falls back
    with 503 if AI is unavailable so the UI can offer manual tracing."""
    from app.services import ceph_ai
    practice_id = uuid.UUID(user["practice_id"])
    image = (await db.execute(
        select(PatientImage).where(PatientImage.id == uuid.UUID(body.image_id), PatientImage.practice_id == practice_id)
    )).scalar_one_or_none()
    if not image:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")

    analysis = await _resolve_analysis(db, practice_id, body.analysis_type)
    landmark_keys = (analysis.landmark_keys if analysis and analysis.landmark_keys
                     else ceph_engine.analysis_landmarks(body.analysis_type))
    if not landmark_keys:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown analysis / no landmarks defined")

    try:
        result = await ceph_ai.auto_landmark_image(
            image.storage_path, image.content_type, image.file_name, landmark_keys
        )
    except RuntimeError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            f"AI auto-landmarking unavailable — use manual tracing. ({e})")

    # Fold per-point confidence into the landmark dict so the editor can shade low-confidence points.
    landmarks = {}
    for k, p in result["landmarks"].items():
        landmarks[k] = {"x": p["x"], "y": p["y"], "conf": result["confidence"].get(k)}

    t = CephTracing(
        id=uuid.uuid4(), practice_id=practice_id, patient_id=image.patient_id, image_id=image.id,
        analysis_type=body.analysis_type, landmarks=landmarks, status="draft",
        is_ai_assisted=True, ai_confidence=result["overall"],
        traced_by=uuid.UUID(user["user_id"]) if user.get("user_id") else None,
        notes="AI-proposed landmarks — doctor review required before finalizing.",
    )
    await _recompute(db, practice_id, t)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    await audit_log(db, user["practice_id"], user["user_id"], "ceph.tracing_ai_landmark", "ceph_tracings", str(t.id))
    out = _tracing_dict(t)
    out["ai_overall_confidence"] = result["overall"]
    return out

@router.get("/tracings/{tracing_id}/polygons")
async def tracing_polygons(tracing_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Visual polygon vertex sequences (skeletal/Jarabak/Ricketts/plane lines) derived from the
    tracing's landmarks — the editor + report draw polylines through these."""
    t = await _get_owned(db, user, tracing_id)
    return {"polygons": ceph_engine.polygons_for(t.landmarks or {})}


class ReportRequest(BaseModel):
    format: str = Field("pdf", pattern="^(pdf|png|json|medicaid)$")
    share_with_patient: bool = False


@router.post("/tracings/{tracing_id}/report", status_code=status.HTTP_201_CREATED)
async def generate_report(tracing_id: str, body: ReportRequest, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate a multi-format diagnostic report (PDF/PNG/JSON/Medicaid), store it in the private
    documents bucket, and record it as a PatientDocument so it appears on the chart (and in
    MyOrthoChart if shared). Server-generated + trusted → stored directly (no virus scan)."""
    from app.services import ceph_report
    from app.services import documents as doc_storage
    from app.services.storage import download_file
    from app.models.workflow import PatientDocument
    from app.models.clinical import Patient

    practice_id = uuid.UUID(user["practice_id"])
    t = await _get_owned(db, user, tracing_id)
    patient = (await db.execute(select(Patient).where(Patient.id == t.patient_id))).scalar_one_or_none()
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Patient"
    analysis = await _resolve_analysis(db, practice_id, t.analysis_type)
    analysis_name = analysis.name if analysis else t.analysis_type

    image = (await db.execute(select(PatientImage).where(PatientImage.id == t.image_id))).scalar_one_or_none()
    image_bytes = None
    if image and image.storage_path:
        try:
            image_bytes = await download_file(image.storage_path)
        except Exception:
            image_bytes = None

    content, mime, ext = ceph_report.generate(body.format, _tracing_dict(t), patient_name, analysis_name, image_bytes)

    key = doc_storage.build_key(practice_id, t.patient_id, f"ceph-report.{ext}", mime)
    await doc_storage.store_document(key, content, mime)

    doc = PatientDocument(
        id=uuid.uuid4(), practice_id=practice_id, patient_id=t.patient_id,
        document_type="ceph_report", title=f"Cephalometric Report — {analysis_name} ({body.format.upper()})",
        storage_key=key, original_filename=f"ceph-report.{ext}", mime_type=mime,
        file_size_bytes=len(content), uploaded_by=uuid.UUID(user["user_id"]) if user.get("user_id") else None,
        uploaded_by_type="staff", direction="office_to_patient",
        shared_with_patient=body.share_with_patient, scan_status="clean",
        notes=f"Generated from ceph tracing {t.id}",
    )
    db.add(doc)
    await db.commit()
    await audit_log(db, user["practice_id"], user["user_id"], "ceph.report_generate", "ceph_tracings", str(t.id))
    return {"document_id": str(doc.id), "format": body.format, "mime_type": mime,
            "shared_with_patient": body.share_with_patient, "size_bytes": len(content)}



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


# ── Superimposition / progress tracking (Phase D) ────────────────────────────────

class SuperimpositionCreate(BaseModel):
    baseline_tracing_id: str
    follow_tracing_id: str
    method: str = Field("sn", pattern="^(sn|structural)$")


def _superimp_dict(s) -> dict:
    return {
        "id": str(s.id),
        "patient_id": str(s.patient_id),
        "baseline_tracing_id": str(s.baseline_tracing_id),
        "follow_tracing_id": str(s.follow_tracing_id),
        "method": s.method,
        "unit": s.unit,
        "deltas": s.deltas or {},
        "summary": s.summary or {},
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.post("/superimpositions", status_code=status.HTTP_201_CREATED)
async def create_superimposition(body: SuperimpositionCreate, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Register two FINALIZED tracings of the same patient on stable reference points and compute
    per-landmark change over time (ICS-style progress tracking)."""
    from app.models.ceph import CephSuperimposition
    practice_id = uuid.UUID(user["practice_id"])
    base = await _get_owned(db, user, body.baseline_tracing_id)
    foll = await _get_owned(db, user, body.follow_tracing_id)
    if base.patient_id != foll.patient_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tracings belong to different patients")
    if base.status != "finalized" or foll.status != "finalized":
        raise HTTPException(status.HTTP_409_CONFLICT, "Both tracings must be finalized before superimposition")

    ppm = (base.calibration or {}).get("px_per_mm") if base.calibration else None
    result = ceph_engine.superimpose(base.landmarks or {}, foll.landmarks or {}, body.method, ppm)
    if result.get("error"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, result["error"])

    s = CephSuperimposition(
        id=uuid.uuid4(), practice_id=practice_id, patient_id=base.patient_id,
        baseline_tracing_id=base.id, follow_tracing_id=foll.id,
        method=body.method, unit=result["unit"], deltas=result["deltas"], summary=result["summary"],
        created_by=uuid.UUID(user["user_id"]) if user.get("user_id") else None,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    await audit_log(db, user["practice_id"], user["user_id"], "ceph.superimposition_create", "ceph_superimpositions", str(s.id))
    return _superimp_dict(s)


@router.get("/patients/{patient_id}/superimpositions")
async def list_superimpositions(patient_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.ceph import CephSuperimposition
    rows = (await db.execute(
        select(CephSuperimposition).where(
            CephSuperimposition.patient_id == uuid.UUID(patient_id),
            CephSuperimposition.practice_id == uuid.UUID(user["practice_id"]),
        ).order_by(CephSuperimposition.created_at.desc())
    )).scalars().all()
    return {"superimpositions": [_superimp_dict(s) for s in rows]}
