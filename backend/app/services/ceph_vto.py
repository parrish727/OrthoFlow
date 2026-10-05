"""Ceph Suite Phase E — Visual Treatment Objective (VTO) projection + soft-tissue morph.

Projects a finalized tracing's landmarks FORWARD in time to a predicted treatment target, combining
(a) Ricketts-style growth over the treatment period and (b) planned mechanics (e.g. incisor
retraction/advancement), then estimates the soft-tissue profile response using Holdaway-style
hard→soft response ratios. Output is a predicted TARGET landmark set + a schematic soft-tissue
profile — rendered 2D first; a photo-realistic morph plugs into the morph-provider interface later.

CLINICAL SAFETY: a VTO is a PREDICTION for planning/patient communication, NOT a guaranteed outcome.
Always labeled "predicted — clinician-reviewed"; never shown to a patient without doctor finalize.
Literature: Ricketts/Holdaway VTO; computerized VTO (e.g. Dolphin) has notable error, esp. surgical.
"""
from __future__ import annotations

import math

Point = dict  # {"x": float, "y": float}


# Holdaway-style soft-tissue response ratios (soft-tissue mm change per 1mm hard-tissue change).
# Conservative, well-cited approximations; the clinician reviews/overrides.
SOFT_TISSUE_RATIOS = {
    "UL": 0.75,   # upper lip follows upper incisor retraction ~0.6–0.75:1
    "LL": 0.9,    # lower lip follows lower incisor ~0.9:1
    "Sn": 0.3,    # subnasale minimal
    "Pog_soft": 0.9,  # soft pogonion follows hard pogonion ~1:1
}


def _p(lm: dict, k: str):
    v = lm.get(k)
    if not v or "x" not in v or "y" not in v:
        return None
    return {"x": float(v["x"]), "y": float(v["y"])}


def project_vto(landmarks: dict, params: dict, px_per_mm: float | None) -> dict:
    """Project landmarks to a predicted treatment target.

    params (all optional, mm or months; +x in image space is anterior/forward):
      growth_months: int             — treatment duration (drives Ricketts growth increment)
      u1_retraction_mm: float        — planned upper-incisor retraction (+ = retract/back)
      l1_retraction_mm: float        — planned lower-incisor retraction
      mandibular_growth_mm: float    — explicit forward mandibular growth override

    Returns {"target_landmarks": {...}, "soft_tissue": [profile pts], "assumptions": {...},
             "unit": "mm"|"px"}.  Pixel moves use px_per_mm when provided (else treat mm≈px).
    """
    ppm = px_per_mm or 1.0
    unit = "mm" if px_per_mm else "px"
    gm = float(params.get("growth_months") or 0)
    u1r = float(params.get("u1_retraction_mm") or 0)
    l1r = float(params.get("l1_retraction_mm") or 0)
    # Ricketts: mandible grows ~1-3mm/yr forward+down during active tx; scale by months.
    mand_growth = params.get("mandibular_growth_mm")
    mand_growth = float(mand_growth) if mand_growth is not None else (gm / 12.0) * 2.0  # ~2mm/yr default

    target = {k: dict(v) for k, v in landmarks.items() if _p(landmarks, k)}

    def move(k, dx_mm=0.0, dy_mm=0.0):
        if k in target:
            target[k]["x"] += dx_mm * ppm
            target[k]["y"] += dy_mm * ppm

    # Mandibular growth: carry B, Pog/Me and lower structures forward (+x) and slightly down (+y).
    for k in ("B", "Me", "Go", "Pog", "L1T", "L1A", "LL", "Pog_soft"):
        move(k, dx_mm=mand_growth, dy_mm=mand_growth * 0.4)

    # Incisor retraction moves the incisor tips posteriorly (−x).
    move("U1T", dx_mm=-u1r)
    move("U1A", dx_mm=-u1r * 0.3)   # apex moves less (controlled tipping/translation)
    move("L1T", dx_mm=-l1r)
    move("L1A", dx_mm=-l1r * 0.3)

    # Soft-tissue response (Holdaway ratios) relative to the driving hard-tissue change.
    # UL follows U1 retraction; LL follows L1; Sn minimal; soft pogonion follows mandibular growth.
    def soft_follow(soft_k, driver_dx_mm, ratio):
        if soft_k in target:
            target[soft_k]["x"] += driver_dx_mm * ratio * ppm

    soft_follow("UL", -u1r, SOFT_TISSUE_RATIOS["UL"])
    soft_follow("LL", -l1r + mand_growth, SOFT_TISSUE_RATIOS["LL"])
    soft_follow("Sn", -u1r, SOFT_TISSUE_RATIOS["Sn"])

    # Schematic soft-tissue profile polyline (upper→lower face), present points only.
    profile_order = ["Sn", "UL", "LL", "Pog_soft", "Me"]
    soft_tissue = [target[k] for k in profile_order if k in target]

    return {
        "target_landmarks": target,
        "soft_tissue": soft_tissue,
        "unit": unit,
        "assumptions": {
            "growth_months": gm,
            "mandibular_growth_mm": round(mand_growth, 2),
            "u1_retraction_mm": u1r,
            "l1_retraction_mm": l1r,
            "soft_tissue_ratios": SOFT_TISSUE_RATIOS,
            "method": "ricketts_growth+holdaway_soft_tissue",
        },
        "disclaimer": "Predicted treatment objective for planning/communication — clinician-reviewed, "
                      "not a guaranteed outcome.",
    }


# ── Photo-realistic morph scaffold (interface only; 2D schematic ships now) ───────────────────────
# A future generative/warp backend implements MorphProvider.render(profile_photo, src_soft_landmarks,
# target_soft_landmarks) -> morphed image bytes. Until then, status() reports 'schematic'.

class MorphProvider:
    """Interface a photo-morph backend will implement (thin-plate-spline warp or generative model)."""
    name = "none"

    async def render(self, profile_photo: bytes, src_soft: dict, target_soft: dict) -> bytes:  # pragma: no cover
        raise NotImplementedError


def morph_status() -> dict:
    """Report soft-tissue morph capability. Photo-realistic morph is scaffolded, not yet active;
    the 2D schematic soft-tissue profile line ships now."""
    return {
        "schematic_profile": True,
        "photo_realistic": False,
        "message": "2D schematic soft-tissue profile available. Photo-realistic morph is scaffolded "
                   "(needs a calibrated profile photo + soft-tissue landmark correspondence + a "
                   "morph provider) and will activate without changing callers.",
    }
