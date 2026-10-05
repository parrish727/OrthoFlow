"""OrthoFlow — Cephalometric Tracing & Analysis models (Ceph Suite Phase A).

A tracing attaches to an existing PatientImage (a lateral ceph radiograph). Landmark coordinates
are stored once per tracing (image pixel space); measurements are DERIVED from landmarks via the
measurement engine (not stored as the source of truth, but cached for display/report). Calibration
(pixels→mm) supports auto-scaling + interactive dynamic refinement.

Clinical safety: an AI-assisted tracing is a DRAFT requiring doctor review; nothing is auto-
finalized. status = draft | finalized.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CephTracing(Base):
    """A cephalometric tracing of one lateral ceph image.

    landmarks: {"S": {"x": 123.0, "y": 456.0}, "N": {...}, ...} in IMAGE PIXEL coordinates.
    measurements: cached derived values {"SNA": {"value": 82.1, "unit": "deg", "norm": 82, "sd": 2,
                   "status": "normal|high|low"}, ...}
    calibration: {"px_per_mm": 11.8, "method": "known_distance|ruler|dpi", "ref_mm": 20.0,
                   "ref_px": 236.0} — pixels→mm for linear measurements.
    """
    __tablename__ = "ceph_tracings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient_images.id"), nullable=False)

    analysis_type: Mapped[str] = mapped_column(String(40), nullable=False, default="abo")  # abo|steiner|downs|mcnamara|wits|jarabak|custom
    landmarks: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    measurements: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    calibration: Mapped[dict | None] = mapped_column(JSONB)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft|finalized
    is_ai_assisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_confidence: Mapped[float | None] = mapped_column(Float)  # overall AI landmark confidence 0-1 (Phase B)

    traced_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_ceph_tracing_patient", "practice_id", "patient_id"),
        Index("idx_ceph_tracing_image", "image_id"),
    )


class CephAnalysisDefinition(Base):
    """A named cephalometric analysis — which landmarks it needs + which measurements it computes.

    Built-in analyses (ABO/Steiner/Downs/McNamara/Wits/Jarabak) are seeded with is_builtin=True and
    practice_id NULL (global). Practices can define CUSTOM analyses (practice-scoped) selecting
    landmarks + measurements (by key, resolved against the measurement engine registry).

    measurement_keys: ["SNA","SNB","ANB","wits",...] — keys the engine knows how to compute.
    landmark_keys: ["S","N","A","B","Go","Me",...] — landmarks required for those measurements.
    """
    __tablename__ = "ceph_analysis_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("practices.id"))  # NULL = global built-in
    key: Mapped[str] = mapped_column(String(40), nullable=False)  # abo|steiner|... or custom slug
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    landmark_keys: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    measurement_keys: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_ceph_analysis_practice", "practice_id", "key"),
    )


class CephSuperimposition(Base):
    """Registers two finalized cephalometric tracings of the same patient on stable reference points
    (anterior cranial base S–N by default) to visualize change over time — the ICS progress-tracking
    analog. Stores computed per-landmark deltas and a summary (growth + treatment change).

    deltas: {"<landmark>": {"dx": mm, "dy": mm, "total": mm}, ...}
    """
    __tablename__ = "ceph_superimpositions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    baseline_tracing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ceph_tracings.id"), nullable=False)
    follow_tracing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ceph_tracings.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False, default="sn")  # sn|structural
    unit: Mapped[str] = mapped_column(String(4), nullable=False, default="mm")
    deltas: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_ceph_superimp_patient", "practice_id", "patient_id"),
    )


class CephVTO(Base):
    """Visual Treatment Objective — a predicted treatment target projected from a finalized tracing
    (Ricketts growth + planned mechanics) with a Holdaway-style soft-tissue response. The output is
    a target landmark set + schematic soft-tissue profile (2D). Photo-realistic morph is scaffolded
    via profile_photo_key + soft_tissue_landmarks + morph_provider (not yet rendered).

    status: draft | finalized (doctor sign-off before any patient-facing use — it's a PREDICTION).
    """
    __tablename__ = "ceph_vtos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    source_tracing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ceph_tracings.id"), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    target_landmarks: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    soft_tissue: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # {"profile":[pts], "assumptions":{}}
    unit: Mapped[str] = mapped_column(String(4), nullable=False, default="mm")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # Photo-morph scaffold (not yet rendered):
    profile_photo_key: Mapped[str | None] = mapped_column(String(512))        # object key for a lateral profile photo
    soft_tissue_landmarks: Mapped[dict | None] = mapped_column(JSONB)         # photo soft-tissue landmark correspondence
    morph_provider: Mapped[str | None] = mapped_column(String(40))           # which morph backend, when active
    morph_result_key: Mapped[str | None] = mapped_column(String(512))        # morphed image object key, when rendered
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_ceph_vto_patient", "practice_id", "patient_id"),
    )


class CephCBCTScan(Base):
    """A 3D CBCT volume (greenfield DICOM ingest; Romexis/Planmeca export → DICOM → here).

    3D landmark geometry is produced by a SELF-HOSTED model (nnU-Net/nnLandmark) when wired; until
    then landmarks can be entered manually. The diagnostic INTERPRETATION/report is generated by the
    higher-tier Anthropic model (ANTHROPIC_CBCT_MODEL, default Opus) reasoning over computed
    measurements. Beta-labeled, supervised. status: uploaded | landmarked | interpreted.

    landmarks_3d: {"<key>": {"x":,"y":,"z":}} in volume voxel/mm space.
    """
    __tablename__ = "ceph_cbct_scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("practices.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    image_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patient_images.id"))
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    source_software: Mapped[str | None] = mapped_column(String(60))   # e.g. "Romexis/Planmeca"
    dicom_study_uid: Mapped[str | None] = mapped_column(String(128))
    dicom_series_uid: Mapped[str | None] = mapped_column(String(128))
    dicom_metadata: Mapped[dict | None] = mapped_column(JSONB)
    voxel_spacing_mm: Mapped[dict | None] = mapped_column(JSONB)       # {"x":,"y":,"z":}
    landmarks_3d: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    measurements_3d: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    interpretation: Mapped[str | None] = mapped_column(Text)          # Opus-generated, clinician-reviewed
    geometry_provider: Mapped[str | None] = mapped_column(String(40))  # self-hosted model id when used
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("idx_ceph_cbct_patient", "practice_id", "patient_id"),
        Index("idx_ceph_cbct_study", "dicom_study_uid"),
    )
