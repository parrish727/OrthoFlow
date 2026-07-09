"""S3-compatible storage service (MinIO locally, AWS S3 in prod).

Uses run_in_executor to avoid blocking the async event loop with synchronous boto3 calls.
"""
import asyncio
import functools
import boto3
from app.core.config import settings

_client = None
_lock = asyncio.Lock()


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
        # Ensure bucket exists
        try:
            _client.head_bucket(Bucket=settings.S3_BUCKET)
        except Exception:
            _client.create_bucket(Bucket=settings.S3_BUCKET)
    return _client


async def _run_sync(func, *args, **kwargs):
    """Run a synchronous function in the default thread executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))


async def upload_file(key: str, content: bytes, content_type: str = "application/pdf") -> None:
    """Upload file to S3/MinIO (non-blocking)."""
    client = _get_client()
    await _run_sync(
        client.put_object,
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type,
    )


async def download_file(key: str) -> bytes:
    """Download file from S3/MinIO (non-blocking)."""
    client = _get_client()

    def _download():
        resp = client.get_object(Bucket=settings.S3_BUCKET, Key=key)
        return resp["Body"].read()

    return await _run_sync(_download)


async def get_presigned_url(key: str, expires: int = 3600) -> str:
    """Generate a presigned download URL (non-blocking)."""
    client = _get_client()
    return await _run_sync(
        client.generate_presigned_url,
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
