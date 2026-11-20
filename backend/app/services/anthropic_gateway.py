"""The only door to the Anthropic API.

Every AI feature calls this module. It scrubs the prompt with a DeidSession, fails closed if any
identifier survives, sends the placeholder-only prompt, then restores the real values in the
answer. A unit test (tests/test_anthropic_gateway_guard.py) fails if any other module calls the
Anthropic API directly, so this rule cannot quietly erode.

No patient data is logged here. Errors carry a short generic message only.
"""
from __future__ import annotations

import base64
import io
import logging

import httpx

from app.core.config import settings
from app.services.deid import DeidError, DeidSession, TOKEN_INSTRUCTION

logger = logging.getLogger(__name__)
_URL = "https://api.anthropic.com/v1/messages"


class GatewayError(Exception):
    """kind: not_configured | timeout | unavailable | deid | disabled"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


def _headers() -> dict:
    return {"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
            "content-type": "application/json"}


def _system(deid: DeidSession, extra: str | None) -> str | None:
    parts = []
    if deid.has_tokens():
        parts.append(TOKEN_INSTRUCTION)
    if extra:
        parts.append(extra)
    return "\n\n".join(parts) or None


def prepare(text: str, deid: DeidSession, aggressive: bool = False) -> str:
    """Scrub and verify. Raises GatewayError('deid') if anything identifying is left."""
    safe = deid.scrub(text, aggressive=aggressive)
    try:
        deid.check(safe)
    except DeidError as e:
        raise GatewayError("deid", "Could not safely prepare this request for AI.") from e
    return safe


async def complete(
    prompt: str,
    deid: DeidSession,
    *,
    max_tokens: int = 2048,
    model: str | None = None,
    system: str | None = None,
    timeout: float = 60.0,
    aggressive: bool = False,
) -> str:
    """Text completion over a de-identified prompt. Returns text with real values restored."""
    if not settings.ANTHROPIC_API_KEY:
        raise GatewayError("not_configured", "AI is not configured")
    safe = prepare(prompt, deid, aggressive=aggressive)
    body: dict = {
        "model": model or settings.ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": safe}],
    }
    sys_text = _system(deid, system)
    if sys_text:
        body["system"] = sys_text
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(_URL, headers=_headers(), json=body, timeout=timeout)
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"]
    except httpx.TimeoutException as e:
        raise GatewayError("timeout", "AI request timed out") from e
    except Exception as e:
        logger.error("anthropic_gateway_error", extra={"error_type": type(e).__name__})
        raise GatewayError("unavailable", "AI service unavailable") from e
    return deid.restore(text)


def strip_image_metadata(data: bytes) -> tuple[bytes, str]:
    """Re-encode an image with no EXIF, text chunks or other metadata. Returns (bytes, media_type).

    Burned-in text (a name printed on the film itself) cannot be removed here. That is why cloud
    image analysis is switchable (CEPH_AI_CLOUD_ENABLED) and why self-hosted analysis is the end goal.
    """
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        fmt = "PNG" if (im.format or "").upper() in ("PNG", "GIF", "WEBP") else "JPEG"
        clean = Image.new(im.mode if im.mode in ("L", "RGB") else "RGB", im.size)
        clean.paste(im.convert(clean.mode))
        buf = io.BytesIO()
        clean.save(buf, format=fmt)
    return buf.getvalue(), ("image/png" if fmt == "PNG" else "image/jpeg")


async def complete_image(
    prompt: str,
    image_bytes: bytes,
    *,
    max_tokens: int = 1500,
    timeout: float = 60.0,
) -> str:
    """Vision completion. Metadata is stripped; the text prompt must contain no patient details."""
    if not settings.ANTHROPIC_API_KEY:
        raise GatewayError("not_configured", "AI not configured (ANTHROPIC_API_KEY unset)")
    if not settings.CEPH_AI_CLOUD_ENABLED:
        raise GatewayError("disabled", "Cloud image analysis is turned off")
    deid = DeidSession()
    safe = prepare(prompt, deid)
    try:
        clean, media = strip_image_metadata(image_bytes)
    except Exception as e:
        raise GatewayError("unavailable", "Image could not be prepared") from e
    body = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media,
                                          "data": base64.standard_b64encode(clean).decode()}},
            {"type": "text", "text": safe},
        ]}],
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(_URL, headers=_headers(), json=body, timeout=timeout)
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
    except httpx.TimeoutException as e:
        raise GatewayError("timeout", "AI landmarking timed out") from e
    except Exception as e:
        logger.error("anthropic_gateway_image_error", extra={"error_type": type(e).__name__})
        raise GatewayError("unavailable", "AI landmarking failed") from e


async def http_complete(prompt: str, deid: DeidSession, *, max_tokens: int = 2048, **kw) -> str:
    """`complete` for route handlers: failures become HTTP errors with generic messages."""
    from fastapi import HTTPException
    try:
        return await complete(prompt, deid, max_tokens=max_tokens, **kw)
    except GatewayError as e:
        code = {"not_configured": 503, "timeout": 503, "unavailable": 503, "deid": 422}.get(e.kind, 503)
        raise HTTPException(code, e.message)
