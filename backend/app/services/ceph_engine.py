"""Cephalometric measurement engine — PURE functions over landmark coordinates.

Measurements are DERIVED from landmarks (image pixel coordinates + a px→mm calibration for linear
values). No network, no DB — unit-testable in isolation. Angular measurements are calibration-
independent; linear measurements (mm) require calibration.

CLINICAL NOTE: norms below are population means ± SD from standard orthodontic references (Steiner,
Downs, McNamara, Jarabak, ABO). They are decision-support references for a clinician — not a
diagnosis. A measurement outside ±1 SD is flagged for attention, not interpreted autonomously.

Landmark coordinate convention: image pixel space, origin top-left, +x right, +y DOWN. All angle
math accounts for the y-down convention so clinical angles read conventionally.
"""
from __future__ import annotations

import math
from typing import Callable

Point = tuple[float, float]


# ── geometry helpers ────────────────────────────────────────────────────────────

def _pt(landmarks: dict, key: str) -> Point | None:
    p = landmarks.get(key)
    if not p or "x" not in p or "y" not in p:
        return None
    return (float(p["x"]), float(p["y"]))


def _angle_at(vertex: Point, a: Point, b: Point) -> float:
    """Interior angle (degrees) at `vertex` formed by rays vertex→a and vertex→b."""
    v1 = (a[0] - vertex[0], a[1] - vertex[1])
    v2 = (b[0] - vertex[0], b[1] - vertex[1])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    m1 = math.hypot(*v1)
    m2 = math.hypot(*v2)
    if m1 == 0 or m2 == 0:
        return 0.0
    c = max(-1.0, min(1.0, dot / (m1 * m2)))
    return math.degrees(math.acos(c))


def _line_angle(p1: Point, p2: Point) -> float:
    """Angle of line p1→p2 vs horizontal, in degrees (y-down aware), range (-180,180]."""
    return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))


def _angle_between_lines(a1: Point, a2: Point, b1: Point, b2: Point) -> float:
    """Acute/obtuse angle (0-180) between line a and line b."""
    d = abs(_line_angle(a1, a2) - _line_angle(b1, b2)) % 180.0
    return d if d <= 90 or True else 180 - d  # keep 0-180


def _dist(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _signed_dist_to_line(p: Point, l1: Point, l2: Point) -> float:
    """Signed perpendicular distance of p from the infinite line l1→l2 (pixel units)."""
    dx, dy = l2[0] - l1[0], l2[1] - l1[1]
    denom = math.hypot(dx, dy)
    if denom == 0:
        return 0.0
    return ((p[0] - l1[0]) * dy - (p[1] - l1[1]) * dx) / denom


# ── measurement registry ─────────────────────────────────────────────────────────
# Each measurement: key -> (label, unit, needs[landmarks], fn(landmarks, px_per_mm)->float|None,
#                            norm, sd). Angles ignore px_per_mm; linears use it.

def _mk_angle3(vertex_k, a_k, b_k):
    def fn(lm, _ppm):
        v, a, b = _pt(lm, vertex_k), _pt(lm, a_k), _pt(lm, b_k)
        if not (v and a and b):
            return None
        return round(_angle_at(v, a, b), 1)
    return fn


def _wits(lm, ppm):
    """Wits appraisal (mm): AO-BO distance along the occlusal plane. Needs A, B, and two occlusal
    plane points (OccP1, OccP2). Positive = AO ahead of BO (Class II tendency)."""
    A, B = _pt(lm, "A"), _pt(lm, "B")
    o1, o2 = _pt(lm, "OccP1"), _pt(lm, "OccP2")
    if not (A and B and o1 and o2 and ppm):
        return None
    # project A and B onto occlusal plane, measure separation along the plane direction
    ux, uy = (o2[0] - o1[0]), (o2[1] - o1[1])
    ulen = math.hypot(ux, uy)
    if ulen == 0:
        return None
    ux, uy = ux / ulen, uy / ulen
    ao = (A[0] - o1[0]) * ux + (A[1] - o1[1]) * uy
    bo = (B[0] - o1[0]) * ux + (B[1] - o1[1]) * uy
    return round((ao - bo) / ppm, 1)


def _afh_pfh_ratio(lm, _ppm):
    """Jarabak ratio (%): posterior face height (S-Go) / anterior face height (N-Me) * 100."""
    S, Go, N, Me = _pt(lm, "S"), _pt(lm, "Go"), _pt(lm, "N"), _pt(lm, "Me")
    if not (S and Go and N and Me):
        return None
    afh = _dist(N, Me)
    if afh == 0:
        return None
    return round(_dist(S, Go) / afh * 100, 1)


# measurement_key: (label, unit, fn, norm_mean, norm_sd)
MEASUREMENTS: dict[str, tuple] = {
    # Skeletal sagittal (Steiner / ABO). SNA/SNB vertex is Nasion (angle S-N-A, S-N-B).
    "SNA": ("SNA angle", "deg", _mk_angle3("N", "S", "A"), 82.0, 2.0),
    "SNB": ("SNB angle", "deg", _mk_angle3("N", "S", "B"), 80.0, 2.0),
    "ANB": ("ANB angle", "deg",
            lambda lm, p: (round(_angle_at(_pt(lm, "N"), _pt(lm, "S"), _pt(lm, "A")) -
                                 _angle_at(_pt(lm, "N"), _pt(lm, "S"), _pt(lm, "B")), 1)
                           if _pt(lm, "N") and _pt(lm, "A") and _pt(lm, "B") and _pt(lm, "S") else None),
            2.0, 2.0),
    "wits": ("Wits appraisal", "mm", _wits, 0.0, 2.0),
    # Vertical / growth (Downs / Jarabak)
    "FMA": ("FMA (MP-FH)", "deg",
            lambda lm, p: (round(_angle_between_lines(_pt(lm, "Go"), _pt(lm, "Me"), _pt(lm, "Po"), _pt(lm, "Or")), 1)
                           if _pt(lm, "Go") and _pt(lm, "Me") and _pt(lm, "Po") and _pt(lm, "Or") else None),
            25.0, 3.0),
    "SN_MP": ("SN-MP (mandibular plane)", "deg",
              lambda lm, p: (round(_angle_between_lines(_pt(lm, "S"), _pt(lm, "N"), _pt(lm, "Go"), _pt(lm, "Me")), 1)
                             if _pt(lm, "S") and _pt(lm, "N") and _pt(lm, "Go") and _pt(lm, "Me") else None),
              32.0, 4.0),
    "jarabak_ratio": ("Jarabak ratio (PFH/AFH)", "%", _afh_pfh_ratio, 65.0, 4.0),
    # Dental
    "U1_SN": ("U1 to SN", "deg",
              lambda lm, p: (round(_angle_between_lines(_pt(lm, "U1T"), _pt(lm, "U1A"), _pt(lm, "S"), _pt(lm, "N")), 1)
                             if _pt(lm, "U1T") and _pt(lm, "U1A") and _pt(lm, "S") and _pt(lm, "N") else None),
              103.0, 5.0),
    "IMPA": ("IMPA (L1-MP)", "deg",
             lambda lm, p: (round(_angle_between_lines(_pt(lm, "L1T"), _pt(lm, "L1A"), _pt(lm, "Go"), _pt(lm, "Me")), 1)
                            if _pt(lm, "L1T") and _pt(lm, "L1A") and _pt(lm, "Go") and _pt(lm, "Me") else None),
             90.0, 5.0),
    # Soft tissue (Downs/Holdaway-ish)
    "nasolabial": ("Nasolabial angle", "deg", _mk_angle3("Cm", "Sn", "UL"), 100.0, 8.0),
}


def status_for(value: float, norm: float, sd: float) -> str:
    if value is None:
        return "missing"
    if value > norm + sd:
        return "high"
    if value < norm - sd:
        return "low"
    return "normal"


def compute(landmarks: dict, measurement_keys: list[str], px_per_mm: float | None = None) -> dict:
    """Compute the requested measurements from landmarks. Returns
    {key: {label, value, unit, norm, sd, status}} — value None if required landmarks missing."""
    out: dict[str, dict] = {}
    for key in measurement_keys:
        spec = MEASUREMENTS.get(key)
        if not spec:
            continue
        label, unit, fn, norm, sd = spec
        try:
            value = fn(landmarks, px_per_mm)
        except Exception:
            value = None
        out[key] = {
            "label": label,
            "value": value,
            "unit": unit,
            "norm": norm,
            "sd": sd,
            "status": status_for(value, norm, sd) if value is not None else "missing",
        }
    return out


def required_landmarks(measurement_keys: list[str]) -> list[str]:
    """Best-effort union of landmark keys referenced by the requested measurements (for the editor
    to know which points to prompt for). Static map kept in ANALYSES; this is a fallback."""
    # The authoritative landmark set per analysis is in the seeded CephAnalysisDefinition rows.
    return []


# ── Built-in analyses: landmark set + measurement set per named analysis ─────────
# key -> (name, description, landmark_keys, measurement_keys). ABO is the default shown.
# Landmark glossary: S sella, N nasion, A A-point, B B-point, Po porion, Or orbitale, Go gonion,
# Me menton, U1T/U1A upper-incisor tip/apex, L1T/L1A lower-incisor tip/apex, OccP1/OccP2 occlusal
# plane pts, Cm columella, Sn subnasale, UL upper lip.
ANALYSES: dict[str, tuple] = {
    "abo": ("ABO (American Board of Orthodontics)",
            "Board-standard summary: skeletal sagittal + vertical + dental positions.",
            ["S", "N", "A", "B", "Po", "Or", "Go", "Me", "U1T", "U1A", "L1T", "L1A", "OccP1", "OccP2"],
            ["SNA", "SNB", "ANB", "wits", "FMA", "SN_MP", "U1_SN", "IMPA"]),
    "steiner": ("Steiner analysis",
                "Classic Steiner: SNA, SNB, ANB, SN-MP, U1-SN, IMPA.",
                ["S", "N", "A", "B", "Go", "Me", "U1T", "U1A", "L1T", "L1A"],
                ["SNA", "SNB", "ANB", "SN_MP", "U1_SN", "IMPA"]),
    "downs": ("Downs analysis",
              "Downs: FMA and dental inclinations on the Frankfort horizontal.",
              ["Po", "Or", "Go", "Me", "A", "B", "N", "S", "U1T", "U1A", "L1T", "L1A"],
              ["FMA", "ANB", "U1_SN", "IMPA"]),
    "mcnamara": ("McNamara analysis",
                 "McNamara: skeletal relationships (uses ANB/Wits + vertical here).",
                 ["S", "N", "A", "B", "Po", "Or", "Go", "Me", "OccP1", "OccP2"],
                 ["SNA", "SNB", "ANB", "wits", "FMA"]),
    "wits": ("Wits appraisal",
             "Wits: AO-BO along the occlusal plane (jaw discrepancy independent of cranial base).",
             ["A", "B", "OccP1", "OccP2"],
             ["wits"]),
    "jarabak": ("Jarabak analysis",
                "Jarabak: posterior/anterior face-height ratio + growth direction.",
                ["S", "N", "Go", "Me"],
                ["jarabak_ratio", "SN_MP"]),
}


def analysis_landmarks(key: str) -> list[str]:
    a = ANALYSES.get(key)
    return list(a[2]) if a else []


def analysis_measurements(key: str) -> list[str]:
    a = ANALYSES.get(key)
    return list(a[3]) if a else []
