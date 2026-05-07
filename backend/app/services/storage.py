"""S3-compatible storage service (MinIO locally, AWS S3 in prod)."""
import boto3
from app.core.config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        kwargs = {
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
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


async def upload_file(key: str, content: bytes, content_type: str = "application/pdf"):
    client = _get_client()
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type,
    )


async def download_file(key: str) -> bytes:
    client = _get_client()
    resp = client.get_object(Bucket=settings.S3_BUCKET, Key=key)
    return resp["Body"].read()


async def get_presigned_url(key: str, expires: int = 3600) -> str:
    client = _get_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
