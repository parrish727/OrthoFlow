"""Patient document exchange storage helper (office⇄patient).

One object in the private 'orthoflow-documents' MinIO bucket per PatientDocument row. Files are
served ONLY via short-lived presigned URLs after server-side authorization — raw object URLs are
never exposed. HIPAA posture: private bucket (no public read), SSE-S3 at rest (MinIO), presigned
links expire in minutes, every issue is audit-logged by the caller.
"""
from __future__ import annotations

import asyncio
import functools
import uuid

import boto3

from app.core.config import settings

DOCUMENTS_BUCKET = "orthoflow-documents"
PRESIGN_EXPIRY_SECONDS = 300  # 5 minutes

# Extension inferred from the validated content type / filename. Mirrors the scanner allow-list.
_EXT_BY_MIME = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/tiff": "tiff",
    "image/heic": "heic",
    "image/heif": "heif",
    "image/webp": "webp",
}

_client = None


def _get_client():
    global _client
    if _client is None:
        kwargs = {
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
            "region_name": "us-east-1",
        }
        if settings.S3_ENDPOINT:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT
        _client = boto3.client("s3", **kwargs)
        # Ensure the private documents bucket exists (private by default — no public policy set).
        try:
            _client.head_bucket(Bucket=DOCUMENTS_BUCKET)
        except Exception:
            _client.create_bucket(Bucket=DOCUMENTS_BUCKET)
    return _client


async def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))


def ext_for(filename: str, mime_type: str | None) -> str:
    """Resolve a safe file extension from the original filename, falling back to the MIME type."""
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in {"pdf", "png", "jpg", "jpeg", "tiff", "tif", "heic", "heif", "webp"}:
            return "jpg" if ext == "jpeg" else ext
    return _EXT_BY_MIME.get((mime_type or "").lower(), "bin")


def build_key(practice_id, patient_id, filename: str, mime_type: str | None) -> str:
    """Deterministic, collision-free object key: practice_id/patient_id/<uuid>.<ext>."""
    ext = ext_for(filename, mime_type)
    return f"{practice_id}/{patient_id}/{uuid.uuid4()}.{ext}"


async def store_document(key: str, content: bytes, content_type: str) -> None:
    """Upload the (already-scanned) document bytes to the private documents bucket."""
    client = _get_client()
    await _run_sync(
        client.put_object,
        Bucket=DOCUMENTS_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type or "application/octet-stream",
    )


async def issue_download_url(key: str, download_name: str | None = None) -> str:
    """Return a short-lived presigned GET URL for the given object key.

    Authorization MUST be enforced by the caller (staff for the practice, or the owning patient)
    BEFORE calling this — this function only mints the time-boxed link.
    """
    client = _get_client()
    params = {"Bucket": DOCUMENTS_BUCKET, "Key": key}
    if download_name:
        params["ResponseContentDisposition"] = f'attachment; filename="{download_name}"'
    return await _run_sync(
        client.generate_presigned_url,
        "get_object",
        Params=params,
        ExpiresIn=PRESIGN_EXPIRY_SECONDS,
    )


async def delete_document(key: str) -> None:
    """Best-effort delete (used to roll back a failed upload)."""
    client = _get_client()
    try:
        await _run_sync(client.delete_object, Bucket=DOCUMENTS_BUCKET, Key=key)
    except Exception:
        pass
