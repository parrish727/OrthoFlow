"""Tests for Ceph Phase F — 3D CBCT geometry + status (CI-safe; no live model/API)."""
import math
from app.services import ceph_cbct as C


def test_angle3_right_angle():
    assert round(C._angle3((0, 0, 0), (0, 1, 0), (1, 0, 0)), 1) == 90.0


def test_dist3():
    assert C._dist3((0, 0, 0), (1, 2, 2)) == 3.0


def test_compute_3d_anb_is_sna_minus_snb():
    lm = {
        "S": {"x": 0, "y": 0, "z": 0}, "N": {"x": 20, "y": 2, "z": 0},
        "A": {"x": 24, "y": -18, "z": 0}, "B": {"x": 22, "y": -30, "z": 0},
    }
    m = C.compute_3d(lm)
    assert round(m["SNA"]["value"] - m["SNB"]["value"], 1) == m["ANB"]["value"]


def test_compute_3d_facial_width_is_3d_only():
    lm = {"GoL": {"x": -5, "y": -28, "z": 40}, "GoR": {"x": -5, "y": -28, "z": -40}}
    m = C.compute_3d(lm)
    assert m["facial_width"]["value"] == 80.0  # |40 - (-40)| in z
    assert m["facial_width"]["unit"] == "mm"


def test_compute_3d_missing_landmarks_missing_status():
    m = C.compute_3d({"S": {"x": 0, "y": 0, "z": 0}})
    assert m["SNA"]["value"] is None and m["SNA"]["status"] == "missing"


def test_geometry_status_manual_by_default_opus_interpretation():
    s = C.geometry_status()
    assert s["mode"] == "manual"          # self-hosted model dormant by default
    assert s["enabled"] is False
    assert "opus" in s["interpretation_model"].lower()
