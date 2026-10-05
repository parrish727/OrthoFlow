"""Ceph Suite Phase F — 3D CBCT geometry provider + Opus interpretation.

Architecture (approved-provider split, grounded in the research):
  • 3D LANDMARK GEOMETRY on a CBCT volume is produced by a SELF-HOSTED model (nnU-Net/nnLandmark
    family) — NOT a general LLM. That provider is scaffolded here and stays DORMANT until a real
    endpoint is wired (CBCT_GEOMETRY_ENABLED/CBCT_GEOMETRY_URL). Manual 3D landmark entry works now.
  • The diagnostic INTERPRETATION/report (reasoning over computed measurements) uses the higher-tier
    Anthropic model (ANTHROPIC_CBCT_MODEL, default Opus). Language only — never geometry.

Beta-labeled, supervised. 3D measurements use true 3D angle/distance over voxel/mm landmark coords.
"""
from __future__ import annotations

import math

from app.core.config import settings

Point3 = tuple[float, float, float]


def geometry_status() -> dict:
    """Report the self-hosted 3D geometry provider readiness."""
    configured = bool(settings.CBCT_GEOMETRY_ENABLED and settings.CBCT_GEOMETRY_URL)
    return {
        "enabled": settings.CBCT_GEOMETRY_ENABLED,
        "configured": configured,
        "mode": "auto" if configured else "manual",
        "interpretation_model": settings.ANTHROPIC_CBCT_MODEL,
        "message": (
            "Self-hosted 3D landmark model active."
            if configured else
            "3D auto-landmarking is scaffolded (self-hosted nnU-Net/nnLandmark). Enter 3D landmarks "
            "manually for now; auto-detection activates when CBCT_GEOMETRY_URL is provisioned. "
            "Diagnostic interpretation uses " + settings.ANTHROPIC_CBCT_MODEL + "."
        ),
    }


def _p3(lm: dict, k: str) -> Point3 | None:
    v = lm.get(k)
    if not v or "x" not in v or "y" not in v or "z" not in v:
        return None
    return (float(v["x"]), float(v["y"]), float(v["z"]))


def _angle3(vertex: Point3, a: Point3, b: Point3) -> float:
    v1 = (a[0] - vertex[0], a[1] - vertex[1], a[2] - vertex[2])
    v2 = (b[0] - vertex[0], b[1] - vertex[1], b[2] - vertex[2])
    dot = sum(c1 * c2 for c1, c2 in zip(v1, v2))
    m1 = math.sqrt(sum(c * c for c in v1))
    m2 = math.sqrt(sum(c * c for c in v2))
    if m1 == 0 or m2 == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (m1 * m2)))))


def _dist3(a: Point3, b: Point3) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


# 3D analogues of the core skeletal measurements (angles are spacing-independent; distances are mm
# when voxel spacing is isotropic/pre-scaled). ANB = SNA - SNB for consistency.
def compute_3d(landmarks: dict) -> dict:
    out: dict[str, dict] = {}

    def ang(k, vertex, a, b, norm, sd):
        v, pa, pb = _p3(landmarks, vertex), _p3(landmarks, a), _p3(landmarks, b)
        val = round(_angle3(v, pa, pb), 1) if (v and pa and pb) else None
        out[k] = {"label": k, "value": val, "unit": "deg", "norm": norm, "sd": sd,
                  "status": _status(val, norm, sd)}
        return val

    sna = ang("SNA", "N", "S", "A", 82.0, 2.0)
    snb = ang("SNB", "N", "S", "B", 80.0, 2.0)
    if sna is not None and snb is not None:
        anb = round(sna - snb, 1)
        out["ANB"] = {"label": "ANB", "value": anb, "unit": "deg", "norm": 2.0, "sd": 2.0,
                      "status": _status(anb, 2.0, 2.0)}
    # facial width (bigonial-ish) if gonion L/R present — a genuinely 3D-only measure.
    gl, gr = _p3(landmarks, "GoL"), _p3(landmarks, "GoR")
    if gl and gr:
        out["facial_width"] = {"label": "Bigonial width", "value": round(_dist3(gl, gr), 1),
                               "unit": "mm", "norm": 95.0, "sd": 6.0, "status": "normal"}
    return out


def _status(value, norm, sd) -> str:
    if value is None:
        return "missing"
    if value > norm + sd:
        return "high"
    if value < norm - sd:
        return "low"
    return "normal"


async def auto_landmark_3d(storage_key: str) -> dict:
    """Call the self-hosted 3D model for landmark geometry. Dormant until provisioned."""
    if not (settings.CBCT_GEOMETRY_ENABLED and settings.CBCT_GEOMETRY_URL):
        raise RuntimeError("3D geometry model not configured — enter landmarks manually")
    import httpx
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{settings.CBCT_GEOMETRY_URL}/landmarks", json={"storage_key": storage_key})
        resp.raise_for_status()
        return resp.json()


async def interpret(patient_name: str, measurements_3d: dict) -> str:
    """Generate a clinician-reviewed diagnostic interpretation of the 3D measurements using the
    higher-tier Anthropic model (language reasoning over numbers, not geometry)."""
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("AI not configured")
    import httpx, json
    rows = "\n".join(
        f"- {m.get('label', k)}: {m.get('value')}{m.get('unit', '')} (norm {m.get('norm')}±{m.get('sd')}, {m.get('status')})"
        for k, m in measurements_3d.items()
    )
    prompt = (
        "You are assisting a board-certified orthodontist. Given these 3D cephalometric measurements "
        f"for patient {patient_name}, write a concise, clinically useful DRAFT interpretation (skeletal "
        "class, vertical pattern, notable deviations, and what to confirm). This is decision-support "
        "the orthodontist will review and edit — do not give definitive diagnosis or treatment orders.\n\n"
        f"{rows}\n"
    )
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": settings.ANTHROPIC_CBCT_MODEL, "max_tokens": 1200,
                  "messages": [{"role": "user", "content": prompt}]},
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
