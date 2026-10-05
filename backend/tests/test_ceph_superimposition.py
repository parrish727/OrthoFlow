"""Tests for Ceph Phase D superimposition engine — registration recovers true change despite a
different head position between timepoints, and reference points net to ~zero."""
import math
from app.services import ceph_engine as E


def _rigid(points: dict, deg: float, tx: float, ty: float) -> dict:
    """Apply a rigid head-reposition (rotate about origin + translate) to all points."""
    th = math.radians(deg); c, s = math.cos(th), math.sin(th)
    return {k: {"x": (p["x"] * c - p["y"] * s) + tx, "y": (p["x"] * s + p["y"] * c) + ty}
            for k, p in points.items()}


def test_reference_points_net_zero():
    base = {"S": {"x": 300, "y": 300}, "N": {"x": 500, "y": 300}, "B": {"x": 550, "y": 560}}
    follow = _rigid(base, 20, 50, -30)  # pure head reposition, no anatomical change
    r = E.superimpose(base, follow, "sn", baseline_ppm=12.0)
    assert r["deltas"]["S"]["total"] == 0.0
    assert r["deltas"]["N"]["total"] == 0.0
    assert r["deltas"]["B"]["total"] < 0.05  # no real change → ~0 after registration


def test_recovers_true_change_under_reposition():
    base = {"S": {"x": 300, "y": 300}, "N": {"x": 500, "y": 300}, "B": {"x": 550, "y": 560}}
    anat = {"S": {"x": 300, "y": 300}, "N": {"x": 500, "y": 300}, "B": {"x": 574, "y": 560}}  # +24px
    follow = _rigid(anat, 15, 40, -25)
    r = E.superimpose(base, follow, "sn", baseline_ppm=12.0)
    assert r["unit"] == "mm"
    assert abs(r["deltas"]["B"]["total"] - 2.0) < 0.05  # 24px / 12ppm = 2mm
    assert r["summary"]["notable"] == ["B"]


def test_pixels_when_uncalibrated():
    base = {"S": {"x": 0, "y": 0}, "N": {"x": 100, "y": 0}, "B": {"x": 50, "y": 50}}
    follow = {"S": {"x": 0, "y": 0}, "N": {"x": 100, "y": 0}, "B": {"x": 60, "y": 50}}
    r = E.superimpose(base, follow, "sn", baseline_ppm=None)
    assert r["unit"] == "px"
    assert abs(r["deltas"]["B"]["total"] - 10.0) < 0.01


def test_missing_reference_points_errors():
    r = E.superimpose({"B": {"x": 1, "y": 2}}, {"B": {"x": 3, "y": 4}}, "sn", 12.0)
    assert "error" in r and r["deltas"] == {}
