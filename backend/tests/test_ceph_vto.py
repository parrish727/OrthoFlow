"""Tests for Ceph Phase E — VTO projection + soft-tissue morph scaffold (pure, CI-safe)."""
from app.services import ceph_vto as V


_LM = {
    "U1T": {"x": 600, "y": 500}, "U1A": {"x": 560, "y": 440},
    "L1T": {"x": 590, "y": 560}, "L1A": {"x": 560, "y": 630},
    "B": {"x": 545, "y": 600}, "Me": {"x": 520, "y": 720}, "Go": {"x": 250, "y": 620},
    "UL": {"x": 615, "y": 470}, "LL": {"x": 610, "y": 540}, "Sn": {"x": 600, "y": 430},
    "Pog_soft": {"x": 560, "y": 650},
}


def test_incisor_retraction_moves_tip_posterior():
    r = V.project_vto(_LM, {"u1_retraction_mm": 3}, px_per_mm=10.0)
    # 3mm retraction * 10 px/mm = -30px on U1T
    assert r["target_landmarks"]["U1T"]["x"] == 600 - 30
    assert r["unit"] == "mm"


def test_mandibular_growth_moves_B_forward():
    r = V.project_vto(_LM, {"mandibular_growth_mm": 2}, px_per_mm=10.0)
    assert r["target_landmarks"]["B"]["x"] == 545 + 20  # +2mm forward


def test_soft_tissue_follows_incisor_by_holdaway_ratio():
    r = V.project_vto(_LM, {"u1_retraction_mm": 4}, px_per_mm=10.0)
    # UL follows U1 retraction (-40px) * 0.75 = -30px
    assert round(r["target_landmarks"]["UL"]["x"], 1) == round(615 - 40 * 0.75, 1)


def test_growth_months_default_mandibular_increment():
    r = V.project_vto(_LM, {"growth_months": 12}, px_per_mm=10.0)
    # 12 months => ~2mm/yr default => B forward ~20px
    assert r["assumptions"]["mandibular_growth_mm"] == 2.0
    assert r["target_landmarks"]["B"]["x"] == 545 + 20


def test_soft_tissue_profile_points_present():
    r = V.project_vto(_LM, {"u1_retraction_mm": 2}, px_per_mm=10.0)
    assert len(r["soft_tissue"]) == 5  # Sn, UL, LL, Pog_soft, Me all present


def test_uncalibrated_uses_pixels():
    r = V.project_vto(_LM, {"u1_retraction_mm": 1}, px_per_mm=None)
    assert r["unit"] == "px"


def test_morph_status_schematic_now_photo_scaffolded():
    s = V.morph_status()
    assert s["schematic_profile"] is True
    assert s["photo_realistic"] is False
