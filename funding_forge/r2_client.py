"""Cloudflare R2 storage client for Funding Forge system files.

Uses aioboto3 (S3-compatible) to persist admin documents and artifacts in R2.
This is admin/system storage only and never stores tenant PII.
"""

import importlib.util
import logging
from datetime import UTC, datetime
from typing import Any

from funding_forge.config import settings

logger = logging.getLogger("funding_forge.r2")

HAS_AIOBOTO3 = importlib.util.find_spec("aioboto3") is not None


def r2_enabled() -> bool:
    """Return True when all required R2 credentials are configured and aioboto3 is available."""
    return HAS_AIOBOTO3 and bool(
        settings.r2_account_id
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
        and settings.r2_bucket_name
    )


class R2Client:
    """Minimal async R2 client for upload/download/delete."""

    def __init__(self) -> None:
        if not r2_enabled():
            raise RuntimeError("R2 is not configured")
        import aioboto3

        self._aioboto3 = aioboto3
        self.account_id = settings.r2_account_id
        self.access_key_id = settings.r2_access_key_id
        self.secret_access_key = settings.r2_secret_access_key
        self.bucket_name = settings.r2_bucket_name
        self.endpoint_url = settings.r2_endpoint_url or (f"https://{self.account_id}.r2.cloudflarestorage.com")

    def _client(self):
        session = self._aioboto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name="auto",
        )
        return session.client("s3", endpoint_url=self.endpoint_url)

    async def upload(self, key: str, content: bytes, mime_type: str | None = None) -> dict[str, Any]:
        """Upload bytes to R2 and return metadata."""
        content_type = mime_type or "application/octet-stream"
        async with self._client() as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=key.lstrip("/"),
                Body=content,
                ContentType=content_type,
            )
        return {
            "key": key.lstrip("/"),
            "size": len(content),
            "mime_type": content_type,
            "modified_at": datetime.now(UTC).isoformat(),
        }

    async def download(self, key: str) -> bytes:
        """Download bytes from R2."""
        async with self._client() as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=key.lstrip("/"))
            async with response["Body"] as stream:
                return await stream.read()

    async def delete(self, key: str) -> None:
        """Delete an object from R2."""
        async with self._client() as s3:
            await s3.delete_object(Bucket=self.bucket_name, Key=key.lstrip("/"))
