"""Tests for Ceph Phase C — visual polygons + multi-format report generation (CI-safe)."""
import json
from app.services import ceph_engine as E
from app.services import ceph_report as R

_TRACING = {
    "analysis_type": "abo",
    "status": "finalized",
    "is_ai_assisted": False,
    "calibration": {"px_per_mm": 12.0},
    "landmarks": {
        "S": {"x": 300, "y": 300}, "N": {"x": 520, "y": 280}, "A": {"x": 560, "y": 470},
        "B": {"x": 545, "y": 560}, "Go": {"x": 250, "y": 620}, "Me": {"x": 520, "y": 720},
        "Po": {"x": 230, "y": 360}, "Or": {"x": 470, "y": 380},
    },
    "measurements": {
        "SNA": {"label": "SNA angle", "value": 82.0, "unit": "deg", "norm": 82, "sd": 2, "status": "normal"},
        "ANB": {"label": "ANB angle", "value": 6.0, "unit": "deg", "norm": 2, "sd": 2, "status": "high"},
    },
}


def test_polygons_from_landmarks():
    polys = E.polygons_for(_TRACING["landmarks"])
    assert "skeletal" in polys and "jarabak" in polys and "frankfort" in polys
    # each polygon is a list of >=2 points with x/y
    for pts in polys.values():
        assert len(pts) >= 2 and all("x" in p and "y" in p for p in pts)


def test_polygons_skip_missing_landmarks():
    # Only one landmark present → no polygon can be drawn (needs >=2 points).
    polys = E.polygons_for({"Go": {"x": 1, "y": 2}})
    assert polys == {}
    # Two present vertices of a polygon → that polygon renders as a 2-point polyline.
    polys2 = E.polygons_for({"Go": {"x": 1, "y": 2}, "Me": {"x": 3, "y": 4}})
    assert "mandibular_plane" in polys2 and len(polys2["mandibular_plane"]) == 2


def test_report_json():
    data = json.loads(R.generate("json", _TRACING, "Jane Doe", "ABO", None)[0])
    assert data["report_type"] == "cephalometric_analysis"
    assert data["patient"] == "Jane Doe"
    assert "SNA" in data["measurements"]


def test_report_medicaid_flags_deviations():
    data = json.loads(R.generate("medicaid", _TRACING, "Jane Doe", "ABO", None)[0])
    assert "ANB" in data["notable_deviations"]  # ANB status=high
    assert data["clinician_finalized"] is True


def test_report_png_and_pdf_bytes():
    png, mime_png, ext_png = R.generate("png", _TRACING, "Jane Doe", "ABO", None)
    assert mime_png == "image/png" and ext_png == "png" and png[:8] == b"\x89PNG\r\n\x1a\n"
    pdf, mime_pdf, ext_pdf = R.generate("pdf", _TRACING, "Jane Doe", "ABO", None)
    assert mime_pdf == "application/pdf" and ext_pdf == "pdf" and pdf[:5] == b"%PDF-"


def test_report_default_is_pdf():
    _, mime, _ = R.generate("unknown", _TRACING, "Jane Doe", "ABO", None)
    assert mime == "application/pdf"
