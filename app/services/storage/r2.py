"""
Semptify 5.0 - Cloudflare R2 Storage Provider
Async S3-compatible client using aioboto3.

Role: SYSTEM storage only — not for user files.
User files always stay in the user's own cloud storage (Google Drive / Dropbox / OneDrive).
R2 stores only system-level data that must survive server restarts:
  - Document processing index (analysis results, classification metadata)
  - Folder ID cache (speeds up Google Drive path resolution)
  - Any other ephemeral-but-expensive-to-rebuild system state
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.storage.base import StorageProvider, StorageFile

logger = logging.getLogger("semptify.r2")

try:
    import aioboto3
    HAS_AIOBOTO3 = True
except ImportError:
    HAS_AIOBOTO3 = False
    logger.warning("aioboto3 not installed — R2 storage unavailable. Run: pip install aioboto3")


class R2Provider(StorageProvider):
    """
    Cloudflare R2 storage provider (S3-compatible) using aioboto3.
    System storage only — users never interact with this directly.
    """

    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
    ):
        self.account_id = account_id
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        # R2 endpoint: https://<account_id>.r2.cloudflarestorage.com
        self.endpoint_url = endpoint_url or f"https://{account_id}.r2.cloudflarestorage.com"

    @property
    def provider_name(self) -> str:
        return "r2"

    def _session(self):
        """Create a fresh aioboto3 session."""
        if not HAS_AIOBOTO3:
            raise RuntimeError("aioboto3 is not installed. Run: pip install aioboto3")
        session = aioboto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name="auto",
        )
        return session

    def _client(self):
        """Return an async context manager for an S3 client pointed at R2."""
        return self._session().client(
            "s3",
            endpoint_url=self.endpoint_url,
        )

    # -------------------------------------------------------------------------
    # StorageProvider interface
    # -------------------------------------------------------------------------

    async def is_connected(self) -> bool:
        """Return True if R2 bucket is reachable and credentials are valid."""
        if not HAS_AIOBOTO3:
            return False
        try:
            async with self._client() as s3:
                await s3.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception as exc:
            logger.debug("R2 is_connected failed: %s", exc)
            return False

    async def upload_file(
        self,
        file_content: bytes,
        destination_path: str,
        filename: str,
        mime_type: Optional[str] = None,
    ) -> StorageFile:
        """Upload bytes to R2. Key = destination_path/filename."""
        key = f"{destination_path.strip('/')}/{filename}".lstrip("/")
        content_type = mime_type or "application/octet-stream"

        async with self._client() as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type,
            )

        return StorageFile(
            id=key,
            name=filename,
            path=key,
            size=len(file_content),
            mime_type=content_type,
            modified_at=datetime.now(timezone.utc),
        )

    async def download_file(self, file_path: str) -> bytes:
        """Download object from R2 and return raw bytes."""
        key = file_path.lstrip("/")
        async with self._client() as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=key)
            return await response["Body"].read()

    async def delete_file(self, file_path: str) -> bool:
        """Delete an object from R2. Returns True on success."""
        key = file_path.lstrip("/")
        try:
            async with self._client() as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as exc:
            logger.warning("R2 delete_file failed for %s: %s", key, exc)
            return False

    async def list_files(
        self,
        folder_path: str = "",
        recursive: bool = False,
    ) -> list[StorageFile]:
        """List objects in R2 under folder_path prefix."""
        prefix = folder_path.strip("/")
        if prefix:
            prefix += "/"

        files: list[StorageFile] = []
        paginator_kwargs: dict = {
            "Bucket": self.bucket_name,
            "Prefix": prefix,
        }
        if not recursive:
            paginator_kwargs["Delimiter"] = "/"

        async with self._client() as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(**paginator_kwargs):
                for obj in page.get("Contents", []):
                    key: str = obj["Key"]
                    files.append(StorageFile(
                        id=key,
                        name=key.split("/")[-1],
                        path=key,
                        size=obj.get("Size", 0),
                        mime_type="application/octet-stream",
                        modified_at=obj.get("LastModified", datetime.now(timezone.utc)),
                    ))

        return files

    async def file_exists(self, file_path: str) -> bool:
        """Return True if the object exists in R2."""
        key = file_path.lstrip("/")
        try:
            async with self._client() as s3:
                await s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    async def create_folder(self, folder_path: str) -> bool:
        """R2/S3 has no real folders — this is a no-op (prefixes are implicit)."""
        return True

    # -------------------------------------------------------------------------
    # Convenience helpers used by the system layer
    # -------------------------------------------------------------------------

    async def put_json(self, key: str, data: dict) -> None:
        """Serialize dict to JSON and store it at key."""
        payload = json.dumps(data, indent=2, default=str).encode("utf-8")
        await self.upload_file(
            file_content=payload,
            destination_path="",
            filename=key,
            mime_type="application/json",
        )

    async def get_json(self, key: str) -> Optional[dict]:
        """Fetch and deserialize a JSON object. Returns None if not found."""
        try:
            raw = await self.download_file(key)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None
