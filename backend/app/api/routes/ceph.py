"""OrthoFlow API — Cephalometric Tracing (Ceph Suite Phase A).

Endpoints for the tracing editor: list analyses (built-in + custom), create/get/update a tracing,
recompute measurements from landmarks, set/refine calibration, and finalize (doctor sign-off).
All practice-scoped via JWT. AI-assisted tracings (Phase B) are drafts; finalize requires a user.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
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


# ── 3D CBCT (Phase F) — beta, supervised ─────────────────────────────────────────

@router.get("/cbct/geometry-status")
async def cbct_geometry_status(user: dict = Depends(get_current_user)):
    """Report 3D geometry provider readiness (manual now; self-hosted auto-landmark scaffolded) +
    which Anthropic model does interpretation."""
    from app.services import ceph_cbct
    return ceph_cbct.geometry_status()


@router.post("/cbct/scans", status_code=status.HTTP_201_CREATED)
async def ingest_cbct(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    source_software: str | None = Form(None),
    dicom_study_uid: str | None = Form(None),
    dicom_series_uid: str | None = Form(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a CBCT DICOM volume (greenfield; Romexis/Planmeca export → DICOM → here). Stores in
    the imaging bucket and records a CephCBCTScan. Beta — supervised."""
    from app.models.ceph import CephCBCTScan
    from app.models.clinical import Patient
    from app.services.storage import upload_file
    practice_id = uuid.UUID(user["practice_id"])
    patient = (await db.execute(select(Patient).where(Patient.id == uuid.UUID(patient_id), Patient.practice_id == practice_id))).scalar_one_or_none()
    if not patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    key = f"{practice_id}/{patient_id}/cbct/{uuid.uuid4()}.dcm"
    await upload_file(key, content, file.content_type or "application/dicom")
    scan = CephCBCTScan(
        id=uuid.uuid4(), practice_id=practice_id, patient_id=uuid.UUID(patient_id),
        storage_key=key, source_software=source_software,
        dicom_study_uid=dicom_study_uid, dicom_series_uid=dicom_series_uid, status="uploaded",
        created_by=uuid.UUID(user["user_id"]) if user.get("user_id") else None,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    await audit_log(db, user["practice_id"], user["user_id"], "ceph.cbct_ingest", "ceph_cbct_scans", str(scan.id))
    return _cbct_dict(scan)


class CBCTLandmarks(BaseModel):
    landmarks_3d: dict  # {"<key>": {"x","y","z"}}


@router.patch("/cbct/scans/{scan_id}/landmarks")
async def set_cbct_landmarks(scan_id: str, body: CBCTLandmarks, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Set/update 3D landmarks (manual, or from the self-hosted model) and recompute 3D measurements."""
    from app.models.ceph import CephCBCTScan
    from app.services import ceph_cbct
    scan = await _get_cbct(db, user, scan_id)
    scan.landmarks_3d = body.landmarks_3d
    scan.measurements_3d = ceph_cbct.compute_3d(body.landmarks_3d)
    scan.status = "landmarked"
    await db.commit()
    await db.refresh(scan)
    return _cbct_dict(scan)


@router.post("/cbct/scans/{scan_id}/interpret")
async def interpret_cbct(scan_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate a clinician-reviewed diagnostic interpretation (Opus-tier) over the 3D measurements."""
    from app.models.ceph import CephCBCTScan
    from app.models.clinical import Patient
    from app.services import ceph_cbct
    scan = await _get_cbct(db, user, scan_id)
    if not scan.measurements_3d:
        raise HTTPException(status.HTTP_409_CONFLICT, "Set 3D landmarks before interpreting")
    patient = (await db.execute(select(Patient).where(Patient.id == scan.patient_id))).scalar_one_or_none()
    try:
        text = await ceph_cbct.interpret(f"{patient.first_name} {patient.last_name}" if patient else "Patient", scan.measurements_3d)
    except RuntimeError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Interpretation unavailable: {e}")
    scan.interpretation = text
    scan.status = "interpreted"
    await db.commit()
    await db.refresh(scan)
    await audit_log(db, user["practice_id"], user["user_id"], "ceph.cbct_interpret", "ceph_cbct_scans", str(scan.id))
    return _cbct_dict(scan)


@router.get("/patients/{patient_id}/cbct-scans")
async def list_cbct(patient_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.ceph import CephCBCTScan
    rows = (await db.execute(
        select(CephCBCTScan).where(CephCBCTScan.patient_id == uuid.UUID(patient_id), CephCBCTScan.practice_id == uuid.UUID(user["practice_id"]))
        .order_by(CephCBCTScan.created_at.desc())
    )).scalars().all()
    return {"scans": [_cbct_dict(s) for s in rows]}


def _cbct_dict(s) -> dict:
    return {
        "id": str(s.id), "patient_id": str(s.patient_id), "status": s.status,
        "source_software": s.source_software, "dicom_study_uid": s.dicom_study_uid,
        "landmarks_3d": s.landmarks_3d or {}, "measurements_3d": s.measurements_3d or {},
        "interpretation": s.interpretation, "geometry_provider": s.geometry_provider,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


async def _get_cbct(db, user, scan_id: str):
    from app.models.ceph import CephCBCTScan
    s = (await db.execute(
        select(CephCBCTScan).where(CephCBCTScan.id == uuid.UUID(scan_id), CephCBCTScan.practice_id == uuid.UUID(user["practice_id"]))
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CBCT scan not found")
    return s


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


# ── VTO + soft-tissue morph (Phase E) ────────────────────────────────────────────

class VTOCreate(BaseModel):
    source_tracing_id: str
    growth_months: int | None = Field(None, ge=0, le=120)
    u1_retraction_mm: float | None = Field(None, ge=-10, le=10)
    l1_retraction_mm: float | None = Field(None, ge=-10, le=10)
    mandibular_growth_mm: float | None = Field(None, ge=-10, le=10)


def _vto_dict(v) -> dict:
    return {
        "id": str(v.id),
        "patient_id": str(v.patient_id),
        "source_tracing_id": str(v.source_tracing_id),
        "params": v.params or {},
        "target_landmarks": v.target_landmarks or {},
        "soft_tissue": v.soft_tissue or {},
        "unit": v.unit,
        "status": v.status,
        "morph_provider": v.morph_provider,
        "has_photo_morph": bool(v.morph_result_key),
        "finalized_at": v.finalized_at.isoformat() if v.finalized_at else None,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


@router.get("/vto/morph-status")
async def vto_morph_status(user: dict = Depends(get_current_user)):
    """Report soft-tissue morph capability (schematic now; photo-realistic scaffolded)."""
    from app.services import ceph_vto
    return ceph_vto.morph_status()


@router.post("/vto", status_code=status.HTTP_201_CREATED)
async def create_vto(body: VTOCreate, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Project a predicted treatment objective (VTO) from a FINALIZED tracing + planned mechanics.
    Output is a predicted target landmark set + schematic soft-tissue profile — a PREDICTION for
    planning/communication, clinician-reviewed, not auto-finalized."""
    from app.models.ceph import CephVTO
    from app.services import ceph_vto
    practice_id = uuid.UUID(user["practice_id"])
    src = await _get_owned(db, user, body.source_tracing_id)
    if src.status != "finalized":
        raise HTTPException(status.HTTP_409_CONFLICT, "Source tracing must be finalized before projecting a VTO")

    params = {k: v for k, v in body.model_dump().items() if k != "source_tracing_id" and v is not None}
    ppm = (src.calibration or {}).get("px_per_mm") if src.calibration else None
    result = ceph_vto.project_vto(src.landmarks or {}, params, ppm)

    v = CephVTO(
        id=uuid.uuid4(), practice_id=practice_id, patient_id=src.patient_id, source_tracing_id=src.id,
        params=params, target_landmarks=result["target_landmarks"],
        soft_tissue={"profile": result["soft_tissue"], "assumptions": result["assumptions"],
                     "disclaimer": result["disclaimer"]},
        unit=result["unit"], status="draft",
        created_by=uuid.UUID(user["user_id"]) if user.get("user_id") else None,
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)
    await audit_log(db, user["practice_id"], user["user_id"], "ceph.vto_create", "ceph_vtos", str(v.id))
    return _vto_dict(v)


@router.get("/patients/{patient_id}/vtos")
async def list_vtos(patient_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.ceph import CephVTO
    rows = (await db.execute(
        select(CephVTO).where(
            CephVTO.patient_id == uuid.UUID(patient_id),
            CephVTO.practice_id == uuid.UUID(user["practice_id"]),
        ).order_by(CephVTO.created_at.desc())
    )).scalars().all()
    return {"vtos": [_vto_dict(v) for v in rows]}


@router.post("/vto/{vto_id}/finalize")
async def finalize_vto(vto_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Doctor sign-off on a VTO before any patient-facing use (it is a prediction)."""
    from app.models.ceph import CephVTO
    import datetime as _dt
    v = (await db.execute(
        select(CephVTO).where(CephVTO.id == uuid.UUID(vto_id), CephVTO.practice_id == uuid.UUID(user["practice_id"]))
    )).scalar_one_or_none()
    if not v:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "VTO not found")
    v.status = "finalized"
    v.finalized_at = _dt.datetime.now(_dt.timezone.utc)
    await db.commit()
    await db.refresh(v)
    await audit_log(db, user["practice_id"], user["user_id"], "ceph.vto_finalize", "ceph_vtos", str(v.id))
    return _vto_dict(v)
