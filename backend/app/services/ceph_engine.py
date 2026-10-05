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


# ── Visual polygons: ordered landmark sequences drawn on the tracing canvas / report ─────────────
# Each polygon is an ordered list of landmark keys forming a line/shape. The frontend/report draws
# a polyline through whichever vertices are present (missing landmarks are skipped gracefully).
POLYGONS: dict[str, list[str]] = {
    # Skeletal profile polygon (cranial base → maxilla → mandible)
    "skeletal": ["S", "N", "A", "B", "Me", "Go", "S"],
    # Jarabak quadrilateral (S-N-Go-Me) — growth/face-height assessment
    "jarabak": ["N", "S", "Go", "Me", "N"],
    # Ricketts-style facial triangle-ish line (N-A-Pog/Me)
    "ricketts": ["N", "A", "Me"],
    # Mandibular plane + Frankfort reference lines
    "mandibular_plane": ["Go", "Me"],
    "frankfort": ["Po", "Or"],
    # Dental axes
    "u1_axis": ["U1A", "U1T"],
    "l1_axis": ["L1A", "L1T"],
    "occlusal_plane": ["OccP1", "OccP2"],
}


def polygons_for(landmarks: dict) -> dict[str, list[dict]]:
    """Return {polygon_name: [ {x,y}, ... ]} using only landmarks that are present."""
    out: dict[str, list[dict]] = {}
    for name, keys in POLYGONS.items():
        pts = []
        for k in keys:
            p = landmarks.get(k)
            if p and "x" in p and "y" in p:
                pts.append({"x": float(p["x"]), "y": float(p["y"])})
        if len(pts) >= 2:
            out[name] = pts
    return out


# ── Superimposition (Phase D) ────────────────────────────────────────────────────
# Register a later tracing onto an earlier one on STABLE reference points (anterior cranial base
# S–N by default), then measure how each landmark moved between timepoints. A 2-point similarity
# transform (translate + rotate, scale normalized out via calibration or the reference distance)
# maps the later tracing into the baseline frame so deltas reflect real change, not head position.

# Reference-point pairs per registration method.
SUPERIMPOSITION_REFS = {
    "sn": ["S", "N"],                 # anterior cranial base (Steiner/standard)
    "structural": ["S", "N"],         # (Björk structural uses stable internal structures; S-N proxy here)
}


def _similarity_transform(src_a, src_b, dst_a, dst_b):
    """Return a function mapping a point from src frame to dst frame, aligning src_a→dst_a and the
    direction/scale src_a→src_b onto dst_a→dst_b (translation + rotation + uniform scale)."""
    sdx, sdy = src_b[0] - src_a[0], src_b[1] - src_a[1]
    ddx, ddy = dst_b[0] - dst_a[0], dst_b[1] - dst_a[1]
    s_len = math.hypot(sdx, sdy) or 1e-9
    d_len = math.hypot(ddx, ddy) or 1e-9
    scale = d_len / s_len
    s_ang = math.atan2(sdy, sdx)
    d_ang = math.atan2(ddy, ddx)
    rot = d_ang - s_ang
    cos_r, sin_r = math.cos(rot), math.sin(rot)

    def xf(p):
        # translate to src_a origin, scale+rotate, translate to dst_a
        x, y = p[0] - src_a[0], p[1] - src_a[1]
        xr = (x * cos_r - y * sin_r) * scale
        yr = (x * sin_r + y * cos_r) * scale
        return (dst_a[0] + xr, dst_a[1] + yr)

    return xf


def superimpose(baseline: dict, follow: dict, method: str = "sn",
                baseline_ppm: float | None = None) -> dict:
    """Register `follow` onto `baseline` on the method's reference points and return per-landmark
    deltas. Deltas are in mm when baseline calibration (px/mm) is available, else in pixels.

    Returns {"method", "unit", "registered_on":[refs], "deltas": {k: {dx,dy,total}}, "summary"}.
    dx = horizontal change (+ = anterior/forward in image x), dy = vertical (+ = downward).
    """
    refs = SUPERIMPOSITION_REFS.get(method, SUPERIMPOSITION_REFS["sn"])
    ra, rb = refs[0], refs[1]
    ba, bb = _pt(baseline, ra), _pt(baseline, rb)
    fa, fb = _pt(follow, ra), _pt(follow, rb)
    if not (ba and bb and fa and fb):
        return {"method": method, "unit": "mm" if baseline_ppm else "px",
                "registered_on": refs, "deltas": {}, "summary": {},
                "error": f"Reference points {refs} missing in one or both tracings"}

    xf = _similarity_transform(fa, fb, ba, bb)
    ppm = baseline_ppm or 1.0
    unit = "mm" if baseline_ppm else "px"

    deltas: dict[str, dict] = {}
    for k, p in follow.items():
        bp = _pt(baseline, k)
        fp = _pt(follow, k)
        if not (bp and fp):
            continue
        fx, fy = xf(fp)  # follow point in baseline frame
        dx = (fx - bp[0]) / ppm
        dy = (fy - bp[1]) / ppm
        deltas[k] = {"dx": round(dx, 2), "dy": round(dy, 2), "total": round(math.hypot(dx, dy), 2)}

    moved = {k: v for k, v in deltas.items() if v["total"] >= (0.5 if unit == "mm" else 5)}
    summary = {
        "unit": unit,
        "landmarks_compared": len(deltas),
        "landmarks_moved": len(moved),
        "max_change": max((v["total"] for v in deltas.values()), default=0.0),
        "notable": sorted(moved, key=lambda k: -deltas[k]["total"])[:6],
    }
    return {"method": method, "unit": unit, "registered_on": refs, "deltas": deltas, "summary": summary}
