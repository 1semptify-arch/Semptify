"""Funding Forge storage abstraction: local filesystem or Cloudflare R2."""

import logging
import mimetypes
from pathlib import Path
from typing import Any

import aiofiles

from funding_forge.config import settings

logger = logging.getLogger("funding_forge.storage")


def ensure_uploads_dir() -> None:
    """Create the local uploads directory if it does not exist."""
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)


async def save_file(
    content: bytes,
    filename: str,
    mime_type: str | None = None,
) -> dict[str, Any]:
    """Save file content and return storage metadata.

    Uses R2 when configured; otherwise falls back to local filesystem.
    """
    from funding_forge import r2_client

    if r2_client.r2_enabled() and settings.storage_backend.lower() == "r2":
        key = f"funding_forge/{filename}"
        meta = await r2_client.R2Client().upload(key, content, mime_type)
        meta["storage_type"] = "r2"
        meta["filename"] = filename
        return meta

    ensure_uploads_dir()
    file_path = Path(settings.uploads_dir) / filename
    async with aiofiles.open(file_path, "wb") as out:
        await out.write(content)

    return {
        "storage_type": "local",
        "key": str(file_path),
        "filename": filename,
        "size": len(content),
        "mime_type": mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
    }


async def read_file(storage_type: str, key: str) -> bytes:
    """Read file content by storage type and key/path."""
    if storage_type == "r2":
        from funding_forge import r2_client

        return await r2_client.R2Client().download(key)

    async with aiofiles.open(key, "rb") as inp:
        return await inp.read()


async def delete_file(storage_type: str, key: str) -> None:
    """Delete a stored file."""
    if storage_type == "r2":
        from funding_forge import r2_client

        await r2_client.R2Client().delete(key)
        return

    Path(key).unlink(missing_ok=True)
