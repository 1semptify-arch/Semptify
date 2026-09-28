"""
Local-disk storage provider — dev/god-mode backend.

Implements the StorageProvider interface against a local folder so the app
runs fully (vault, overlays, shares, dual-write paths) without any OAuth.
Selected by get_provider() ONLY when the caller passes the dev god-mode
access token — real cloud providers are never touched by this path.

Root defaults to %LOCALAPPDATA%/SemptifyVault or SEMPTIFY_LOCAL_STORAGE_ROOT.
"""

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from app.services.storage.base import StorageFile, StorageProvider

logger = logging.getLogger(__name__)

DEV_TOKEN = "dev-godmode-token"


def _root() -> Path:
    override = os.environ.get("SEMPTIFY_LOCAL_STORAGE_ROOT")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "SemptifyVault"


class LocalDiskProvider(StorageProvider):
    """Stores the user's 'cloud vault' as plain files under a local root."""

    def __init__(self, **kwargs):
        self.root = _root()
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        return "local"

    def _to_disk(self, path: str) -> Path:
        """Map a vault-style posix path to a path under root. Strips traversal."""
        clean = PurePosixPath("/" + path.lstrip("/"))
        parts = [p for p in clean.parts[1:] if p not in ("..", ".", "")]
        return self.root.joinpath(*parts)

    def _rel(self, disk: Path) -> str:
        return "/" + disk.relative_to(self.root).as_posix()

    def _sf(self, disk: Path) -> StorageFile:
        stat = disk.stat()
        return StorageFile(
            id=self._rel(disk),
            name=disk.name,
            path=self._rel(disk),
            size=0 if disk.is_dir() else stat.st_size,
            mime_type="inode/directory" if disk.is_dir() else "application/octet-stream",
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            is_folder=disk.is_dir(),
        )

    async def is_connected(self) -> bool:
        return self.root.exists()

    async def upload_file(
        self,
        file_content: bytes,
        destination_path: str,
        filename: str,
        mime_type: str | None = None,
    ) -> StorageFile:
        folder = self._to_disk(destination_path)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / filename
        target.write_bytes(file_content)
        sf = self._sf(target)
        sf.mime_type = mime_type or sf.mime_type
        return sf

    async def download_file(self, file_path: str) -> bytes:
        return self._to_disk(file_path).read_bytes()

    async def delete_file(self, file_path: str) -> bool:
        disk = self._to_disk(file_path)
        if not disk.exists():
            return False
        if disk.is_dir():
            shutil.rmtree(disk)
        else:
            disk.unlink()
        return True

    async def list_files(self, folder_path: str = "/", recursive: bool = False) -> list[StorageFile]:
        folder = self._to_disk(folder_path)
        if not folder.exists():
            return []
        out = []
        iterator = folder.rglob("*") if recursive else folder.iterdir()
        for p in iterator:
            if p == folder:
                continue
            out.append(self._sf(p))
        return out

    async def file_exists(self, file_path: str) -> bool:
        return self._to_disk(file_path).exists()

    async def create_folder(self, folder_path: str) -> bool:
        try:
            self._to_disk(folder_path).mkdir(parents=True, exist_ok=True)
            return True
        except OSError as exc:
            logger.error("LocalDiskProvider create_folder failed for %s: %s", folder_path, exc)
            raise RuntimeError(f"create_folder failed: {folder_path}") from exc


__all__ = ["LocalDiskProvider", "DEV_TOKEN"]
