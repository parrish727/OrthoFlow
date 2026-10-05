"""Tests for the cephalometric measurement engine (Ceph Suite Phase A).

Pure geometry — verifies angle/distance/Wits/ratio math against known constructions, the SNA−SNB
= ANB identity, status flagging vs norms, and the analysis registry. Clinical-grade correctness of
this engine is the top risk in the Ceph suite, so these are exact-value assertions.
"""
import math
from app.services import ceph_engine as E


def test_angle_at_right_angle():
    # vertex at origin; rays straight up and straight right → 90°
    assert E._angle_at((0, 0), (0, -10), (10, 0)) == 90.0


def test_angle_at_straight_line():
    assert round(E._angle_at((0, 0), (-10, 0), (10, 0)), 1) == 180.0


def test_distance():
    assert E._dist((0, 0), (3, 4)) == 5.0


def test_sna_vertex_is_nasion():
    # S-N vertical, N-A horizontal → SNA 90°
    lm = {"S": {"x": 0, "y": 0}, "N": {"x": 0, "y": 100}, "A": {"x": 100, "y": 100}}
    r = E.compute(lm, ["SNA"], None)
    assert r["SNA"]["value"] == 90.0


def test_anb_equals_sna_minus_snb():
    lm = {
        "S": {"x": 300, "y": 300}, "N": {"x": 520, "y": 280},
        "A": {"x": 560, "y": 470}, "B": {"x": 545, "y": 560},
    }
    r = E.compute(lm, ["SNA", "SNB", "ANB"], None)
    assert round(r["SNA"]["value"] - r["SNB"]["value"], 1) == r["ANB"]["value"]


def test_wits_mm_uses_calibration():
    # A 20px ahead of B along a horizontal occlusal plane; 10 px/mm → 2.0 mm
    lm = {"A": {"x": 100, "y": 100}, "B": {"x": 80, "y": 100},
          "OccP1": {"x": 0, "y": 100}, "OccP2": {"x": 200, "y": 100}}
    assert E.compute(lm, ["wits"], 10.0)["wits"]["value"] == 2.0


def test_wits_requires_calibration():
    lm = {"A": {"x": 100, "y": 100}, "B": {"x": 80, "y": 100},
          "OccP1": {"x": 0, "y": 100}, "OccP2": {"x": 200, "y": 100}}
    assert E.compute(lm, ["wits"], None)["wits"]["value"] is None


def test_jarabak_ratio():
    # S-Go = 60, N-Me = 100 → 60%
    lm = {"S": {"x": 0, "y": 0}, "Go": {"x": 0, "y": 60},
          "N": {"x": 50, "y": 0}, "Me": {"x": 50, "y": 100}}
    assert E.compute(lm, ["jarabak_ratio"], None)["jarabak_ratio"]["value"] == 60.0


def test_missing_landmarks_yield_missing_status():
    r = E.compute({"S": {"x": 0, "y": 0}}, ["SNA"], None)
    assert r["SNA"]["value"] is None
    assert r["SNA"]["status"] == "missing"


def test_status_flags():
    assert E.status_for(82.0, 82.0, 2.0) == "normal"
    assert E.status_for(85.1, 82.0, 2.0) == "high"
    assert E.status_for(78.9, 82.0, 2.0) == "low"


def test_analysis_registry():
    assert set(E.ANALYSES) == {"abo", "steiner", "downs", "mcnamara", "wits", "jarabak"}
    assert "SNA" in E.analysis_measurements("steiner")
    assert "S" in E.analysis_landmarks("abo")
    # every measurement an analysis references must exist in the engine
    for key in E.ANALYSES:
        for mk in E.analysis_measurements(key):
            assert mk in E.MEASUREMENTS, f"{key} references unknown measurement {mk}"
