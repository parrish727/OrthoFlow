"""Ceph Suite Phase B — AI-assisted auto-landmarking (2D lateral ceph).

Sends the ceph image to the Anthropic vision model (settings.ANTHROPIC_MODEL) and asks it to
locate the requested cephalometric landmarks, returning NORMALIZED coordinates (0..1) + a per-point
confidence. We convert to image pixel coordinates and hand back a DRAFT for mandatory doctor review
— nothing is auto-finalized. If AI is unconfigured/unavailable, callers fall back to manual tracing.

CLINICAL SAFETY: AI landmarks are decision-support only. Per the orthodontic literature, automated
landmarking is reproducible but still requires clinician supervision; the editor shows per-point
confidence and the doctor adjusts before finalizing.
"""
from __future__ import annotations

import base64
import io
import json
import logging

import httpx

from app.core.config import settings
from app.services.storage import download_file

logger = logging.getLogger(__name__)

_LANDMARK_GLOSSARY = {
    "S": "Sella (center of sella turcica)",
    "N": "Nasion (frontonasal suture, most anterior point)",
    "A": "A-point (deepest point of maxillary concavity)",
    "B": "B-point (deepest point of mandibular concavity)",
    "Po": "Porion (superior external auditory meatus)",
    "Or": "Orbitale (lowest point of orbital rim)",
    "Go": "Gonion (angle of the mandible)",
    "Me": "Menton (lowest point of mandibular symphysis)",
    "U1T": "Upper incisor tip (incisal edge of maxillary central incisor)",
    "U1A": "Upper incisor apex (root apex of maxillary central incisor)",
    "L1T": "Lower incisor tip (incisal edge of mandibular central incisor)",
    "L1A": "Lower incisor apex (root apex of mandibular central incisor)",
    "OccP1": "Anterior occlusal plane point (incisal overlap)",
    "OccP2": "Posterior occlusal plane point (distal molar cusp overlap)",
    "Cm": "Columella point (soft tissue)",
    "Sn": "Subnasale (soft tissue)",
    "UL": "Upper lip (labrale superius, soft tissue)",
}


def _media_type(content_type: str | None, filename: str | None) -> str:
    ct = (content_type or "").lower()
    if ct in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        return ct
    name = (filename or "").lower()
    if name.endswith(".png"):
        return "image/png"
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    return "image/png"


def _image_size(data: bytes) -> tuple[int, int] | None:
    """Best-effort image dimensions without a hard Pillow dependency at call time."""
    try:
        from PIL import Image  # Pillow is already a dependency (pdfplumber pulls it)
        with Image.open(io.BytesIO(data)) as im:
            return im.size  # (w, h)
    except Exception:
        return None


def is_configured() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


async def auto_landmark(image_bytes: bytes, content_type: str | None, filename: str | None,
                        landmark_keys: list[str]) -> dict:
    """Return {"landmarks": {key: {x,y}}, "confidence": {key: 0..1}, "overall": 0..1} in IMAGE
    PIXEL coordinates. Raises RuntimeError if AI is unconfigured/unavailable (caller falls back)."""
    if not is_configured():
        raise RuntimeError("AI not configured (ANTHROPIC_API_KEY unset)")

    size = _image_size(image_bytes)
    b64 = base64.standard_b64encode(image_bytes).decode()
    media_type = _media_type(content_type, filename)

    wanted = {k: _LANDMARK_GLOSSARY.get(k, k) for k in landmark_keys}
    prompt = (
        "You are assisting a board-certified orthodontist by proposing cephalometric landmark "
        "locations on this LATERAL CEPHALOGRAM. These are DRAFT suggestions the doctor will review "
        "and correct — do not refuse. For EACH requested landmark, return its location as NORMALIZED "
        "coordinates where x=0 is the left edge, x=1 the right edge, y=0 the TOP edge, y=1 the bottom "
        "edge, plus a confidence 0..1. If a landmark is not visible, set confidence 0 and your best "
        "guess. Respond with ONLY a JSON object, no prose:\n"
        '{"landmarks": {"<KEY>": {"x": <0..1>, "y": <0..1>, "confidence": <0..1>}, ...}}\n\n'
        "Requested landmarks:\n" + "\n".join(f"- {k}: {d}" for k, d in wanted.items())
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.ANTHROPIC_MODEL,
                    "max_tokens": 1500,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                            {"type": "text", "text": prompt},
                        ],
                    }],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"]
    except httpx.TimeoutException as e:
        raise RuntimeError("AI landmarking timed out") from e
    except Exception as e:
        raise RuntimeError(f"AI landmarking failed: {str(e)[:120]}") from e

    parsed = _extract_json(text)
    raw = (parsed or {}).get("landmarks", {})

    w, h = (size or (1000, 1000))
    landmarks: dict[str, dict] = {}
    confidence: dict[str, float] = {}
    for k in landmark_keys:
        p = raw.get(k)
        if not p or "x" not in p or "y" not in p:
            continue
        try:
            nx, ny = float(p["x"]), float(p["y"])
        except (TypeError, ValueError):
            continue
        # clamp normalized then scale to pixels
        nx = min(1.0, max(0.0, nx))
        ny = min(1.0, max(0.0, ny))
        landmarks[k] = {"x": round(nx * w, 1), "y": round(ny * h, 1)}
        try:
            confidence[k] = round(min(1.0, max(0.0, float(p.get("confidence", 0.5)))), 2)
        except (TypeError, ValueError):
            confidence[k] = 0.5

    overall = round(sum(confidence.values()) / len(confidence), 2) if confidence else 0.0
    return {"landmarks": landmarks, "confidence": confidence, "overall": overall,
            "image_size": {"w": w, "h": h}}


def _extract_json(text: str) -> dict | None:
    """Pull the first JSON object out of a model response (handles code fences / stray prose)."""
    if not text:
        return None
    t = text.strip()
    if "```" in t:
        # take the content between the first pair of fences
        parts = t.split("```")
        for seg in parts:
            seg = seg.strip()
            if seg.startswith("json"):
                seg = seg[4:].strip()
            if seg.startswith("{"):
                t = seg
                break
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None


async def auto_landmark_image(storage_path: str, content_type: str | None, filename: str | None,
                              landmark_keys: list[str]) -> dict:
    """Fetch image bytes from storage, then auto-landmark."""
    data = await download_file(storage_path)
    return await auto_landmark(data, content_type, filename, landmark_keys)
