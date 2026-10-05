"""Demo seed for the Cephalometric Suite — gives the flagship demo patient a populated ceph
workflow so a doctor sees the capability immediately (image + tracings + progress + VTO + CBCT).

Idempotent. Generates a real (synthetic) lateral-ceph PNG into MinIO so the Imaging viewer renders
it and the 'Trace & Analyze' action appears, then seeds two FINALIZED tracings (initial + progress),
a superimposition, a finalized VTO, and a CBCT scan with 3D measurements + interpretation.

NOTE for future features: when a new clinical capability ships, add demo mock data here (or a sibling
demo seeder) so the demo always showcases it. This is a standing convention.
"""
import io
import uuid
from datetime import date, datetime, timezone, timedelta

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.clinical import Patient
from app.models.imaging import PatientImage
from app.models.ceph import CephTracing, CephSuperimposition, CephVTO, CephCBCTScan
from app.services import ceph_engine, ceph_vto, ceph_cbct

DEMO_PRACTICE_ID = uuid.UUID("82fe9d87-6250-4b15-ac7d-26de094a4be8")
IMAGING_BUCKET = "orthoflow-imaging"

# Realistic-ish lateral-ceph landmark set (image pixel coords in a 900x1100 frame). Two timepoints:
# initial, then progress where incisors retracted + mandible grew forward slightly.
_INITIAL = {
    "S": {"x": 300, "y": 330}, "N": {"x": 560, "y": 300}, "A": {"x": 600, "y": 520},
    "B": {"x": 585, "y": 640}, "Po": {"x": 250, "y": 400}, "Or": {"x": 520, "y": 430},
    "Go": {"x": 270, "y": 720}, "Me": {"x": 560, "y": 840}, "U1T": {"x": 630, "y": 575},
    "U1A": {"x": 600, "y": 500}, "L1T": {"x": 615, "y": 600}, "L1A": {"x": 590, "y": 680},
    "OccP1": {"x": 470, "y": 600}, "OccP2": {"x": 650, "y": 585},
}
_PROGRESS = {**{k: dict(v) for k, v in _INITIAL.items()}}
_PROGRESS["U1T"] = {"x": 614, "y": 575}   # upper incisor retracted ~16px
_PROGRESS["L1T"] = {"x": 603, "y": 600}
_PROGRESS["B"] = {"x": 592, "y": 642}      # slight mandibular advancement
_PROGRESS["Me"] = {"x": 568, "y": 845}


def _make_ceph_png() -> bytes:
    """Synthetic lateral-ceph-looking grayscale PNG (clearly a demo placeholder, renders fine)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (900, 1100), (18, 20, 26))
    d = ImageDraw.Draw(img)
    # faint skull-ish profile so the viewer shows something recognizable
    d.ellipse((180, 180, 760, 760), outline=(120, 128, 140), width=3)
    d.arc((300, 500, 760, 980), start=300, end=60, fill=(120, 128, 140), width=3)
    d.line((560, 300, 600, 520), fill=(90, 98, 110), width=2)  # nasion->A region
    d.text((40, 40), "DEMO cephalogram — synthetic for product demonstration", fill=(150, 160, 175))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def seed_ceph_demo():
    """Idempotent: seed a populated ceph workflow for the flagship demo patient (Priscilla)."""
    from app.services.storage import upload_file

    async with SessionLocal() as db:
        patient = (await db.execute(
            select(Patient).where(Patient.practice_id == DEMO_PRACTICE_ID, Patient.first_name == "Priscilla")
        )).scalar_one_or_none()
        if not patient:
            print("  ⏭  Ceph demo skipped (Priscilla not found)")
            return
        pid = patient.id

        # Skip if already seeded (an initial-records demo ceph with our marker filename exists).
        existing = (await db.execute(
            select(PatientImage).where(
                PatientImage.patient_id == pid, PatientImage.image_type == "ceph",
                PatientImage.file_name == "demo-ceph-initial.png",
            )
        )).scalar_one_or_none()
        if existing:
            print("  ✅ Ceph demo already seeded")
            return

        today = date.today()
        # 1) Real ceph image in MinIO (initial records, ~8 months ago).
        png = _make_ceph_png()
        key = f"{DEMO_PRACTICE_ID}/{pid}/demo/demo-ceph-initial.png"
        await upload_file(key, png, "image/png")
        img = PatientImage(
            id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=pid, image_type="ceph",
            modality="2D", description="Lateral cephalogram — initial records (demo)",
            storage_path=key, storage_bucket=IMAGING_BUCKET, file_name="demo-ceph-initial.png",
            content_type="image/png", file_size_bytes=len(png), status="active",
            captured_date=today - timedelta(days=240),
        )
        db.add(img)
        await db.flush()

        calib = {"px_per_mm": 11.5, "method": "known_distance", "ref_mm": 20.0, "ref_px": 230.0}
        now = datetime.now(timezone.utc)

        def _tracing(landmarks, when_days):
            t = CephTracing(
                id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=pid, image_id=img.id,
                analysis_type="abo", landmarks=landmarks, calibration=calib,
                status="finalized", is_ai_assisted=False, finalized_at=now,
            )
            t.measurements = ceph_engine.compute(landmarks, ceph_engine.analysis_measurements("abo"), calib["px_per_mm"])
            t.created_at = now - timedelta(days=when_days)
            return t

        t_initial = _tracing(_INITIAL, 240)
        t_progress = _tracing(_PROGRESS, 20)
        db.add_all([t_initial, t_progress])
        await db.flush()

        # 2) Superimposition initial -> progress (shows real change over time).
        sup = ceph_engine.superimpose(_INITIAL, _PROGRESS, "sn", calib["px_per_mm"])
        db.add(CephSuperimposition(
            id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=pid,
            baseline_tracing_id=t_initial.id, follow_tracing_id=t_progress.id,
            method="sn", unit=sup["unit"], deltas=sup["deltas"], summary=sup["summary"],
        ))

        # 3) Finalized VTO projected from the initial tracing (predicted target).
        vto_params = {"growth_months": 12, "u1_retraction_mm": 3, "l1_retraction_mm": 2}
        vres = ceph_vto.project_vto(_INITIAL, vto_params, calib["px_per_mm"])
        db.add(CephVTO(
            id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=pid, source_tracing_id=t_initial.id,
            params=vto_params, target_landmarks=vres["target_landmarks"],
            soft_tissue={"profile": vres["soft_tissue"], "assumptions": vres["assumptions"],
                         "disclaimer": vres["disclaimer"]},
            unit=vres["unit"], status="finalized", finalized_at=now,
        ))

        # 4) CBCT scan with 3D measurements + a canned interpretation (demo — avoids a live model call).
        lm3d = {
            "S": {"x": 0, "y": 0, "z": 0}, "N": {"x": 20, "y": 2, "z": 0},
            "A": {"x": 24, "y": -18, "z": 0}, "B": {"x": 22, "y": -30, "z": 0},
            "GoL": {"x": -5, "y": -28, "z": 40}, "GoR": {"x": -5, "y": -28, "z": -40},
        }
        m3d = ceph_cbct.compute_3d(lm3d)
        db.add(CephCBCTScan(
            id=uuid.uuid4(), practice_id=DEMO_PRACTICE_ID, patient_id=pid, image_id=img.id,
            storage_key=f"{DEMO_PRACTICE_ID}/{pid}/cbct/demo-cbct.dcm", source_software="Romexis/Planmeca",
            dicom_study_uid="DEMO.1.2.840.CBCT", landmarks_3d=lm3d, measurements_3d=m3d, status="interpreted",
            interpretation=(
                "DRAFT 3D cephalometric interpretation (demo). Skeletal Class II tendency "
                "(ANB elevated) with a mildly horizontal growth pattern. Bigonial width within normal "
                "range. Recommend correlating with clinical exam and 2D cephalometric tracing. "
                "For orthodontist review — not a definitive diagnosis."
            ),
        ))

        await db.commit()
        print("  ✅ Ceph demo: 1 image, 2 finalized tracings, 1 superimposition, 1 VTO, 1 CBCT")
