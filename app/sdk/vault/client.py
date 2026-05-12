"""
VaultClient — the single class all Semptify products use for vault operations.

Zero dependencies on FastAPI, SQLAlchemy, middleware, or navigation.
Takes a provider name, access token, and user ID. Does storage operations.

Usage:
    from app.sdk.vault import VaultClient, TENANT_VAULT

    vault = VaultClient(
        provider="google_drive",
        access_token="ya29.xxxxx",
        user_id="GU2L3wyfBy",
        folder_spec=TENANT_VAULT,
    )
    result = await vault.create_folders()
    if result.all_ok:
        print("Vault ready")
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Coroutine, List, Optional, Any

from app.core.vault_paths import VAULT_ROOT
from app.sdk.vault.folder_spec import VaultFolderSpec, TENANT_VAULT
from app.sdk.vault.errors import VaultError, VaultProviderError, VaultFolderError

logger = logging.getLogger("semptify.vault.sdk")


# ============================================================================
# Result Types
# ============================================================================

@dataclass
class FolderResult:
    """Result for a single folder creation/verification attempt."""
    path: str
    status: str  # "ok", "error", "skipped"
    detail: str = ""


@dataclass
class VaultResult:
    """Aggregate result for a vault operation."""
    folders: List[FolderResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(f.status == "ok" for f in self.folders)

    @property
    def failed(self) -> List[FolderResult]:
        return [f for f in self.folders if f.status == "error"]

    @property
    def succeeded(self) -> List[FolderResult]:
        return [f for f in self.folders if f.status == "ok"]

    def to_dict(self) -> dict:
        return {
            "all_ok": self.all_ok,
            "total": len(self.folders),
            "ok_count": len(self.succeeded),
            "error_count": len(self.failed),
            "folders": [
                {"path": f.path, "status": f.status, "detail": f.detail}
                for f in self.folders
            ],
        }


@dataclass
class HealthResult:
    """Result of a vault health check."""
    healthy: bool
    folders_exist: List[str]
    folders_missing: List[str]
    provider_connected: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "healthy": self.healthy,
            "provider_connected": self.provider_connected,
            "folders_exist": self.folders_exist,
            "folders_missing": self.folders_missing,
            "detail": self.detail,
        }


# ============================================================================
# VaultClient
# ============================================================================

class VaultClient:
    """
    Isolated vault management client.

    No database. No FastAPI. No middleware. No navigation.
    Takes a token, manages folders and files in cloud storage.

    Args:
        provider:        Storage provider name ("google_drive", "dropbox", "onedrive")
        access_token:    Valid OAuth access token
        user_id:         Semptify user ID (for encryption key derivation)
        folder_spec:     Which folders to create (defaults to TENANT_VAULT)
        token_refresher: Optional async callback to refresh expired tokens.
                         Signature: async (current_token: str) -> str
        inter_call_delay: Seconds to wait between API calls (rate limit protection)
    """

    __version__ = "1.0.0"

    def __init__(
        self,
        provider: str,
        access_token: str,
        user_id: str,
        folder_spec: Optional[VaultFolderSpec] = None,
        token_refresher: Optional[Callable[[str], Coroutine[Any, Any, str]]] = None,
        inter_call_delay: float = 0.1,
    ):
        self._provider_name = provider
        self._access_token = access_token
        self._user_id = user_id
        self._folder_spec = folder_spec or TENANT_VAULT
        self._token_refresher = token_refresher
        self._inter_call_delay = inter_call_delay
        self._storage = None  # Lazy-initialized

    # ------------------------------------------------------------------
    # Provider (lazy init)
    # ------------------------------------------------------------------

    def _get_storage(self):
        """Get or create the storage provider instance."""
        if self._storage is None:
            from app.services.storage import get_provider
            self._storage = get_provider(
                self._provider_name,
                access_token=self._access_token,
            )
        return self._storage

    # ------------------------------------------------------------------
    # Folder Operations
    # ------------------------------------------------------------------

    async def create_folders(self) -> VaultResult:
        """
        Create all vault folders defined in the folder spec.

        Idempotent — safe to call multiple times. Existing folders are
        left untouched. Returns per-folder status.
        """
        storage = self._get_storage()
        result = VaultResult()

        for folder_path in self._folder_spec.all_folders:
            try:
                print(f"  VAULT_SDK: Creating folder: {folder_path}", flush=True)
                created = await storage.create_folder(folder_path)
                if created:
                    result.folders.append(FolderResult(path=folder_path, status="ok"))
                else:
                    result.folders.append(FolderResult(
                        path=folder_path,
                        status="error",
                        detail="create_folder returned False",
                    ))
            except Exception as exc:
                logger.error("Folder creation failed for %s: %s", folder_path, exc)
                result.folders.append(FolderResult(
                    path=folder_path,
                    status="error",
                    detail=str(exc),
                ))

            # Rate limit protection
            if self._inter_call_delay > 0:
                await asyncio.sleep(self._inter_call_delay)

        if result.all_ok:
            print(f"  VAULT_SDK: All {len(result.folders)} folders created successfully", flush=True)
        else:
            print(f"  VAULT_SDK: {len(result.failed)} folders failed: {[f.path for f in result.failed]}", flush=True)

        return result

    async def verify_folders(self) -> VaultResult:
        """
        Verify that all expected vault folders exist and are accessible.

        Does NOT create missing folders — use create_folders() or repair() for that.
        """
        storage = self._get_storage()
        result = VaultResult()

        for folder_path in self._folder_spec.all_folders:
            try:
                files = await storage.list_files(folder_path)
                if files is not None:
                    result.folders.append(FolderResult(path=folder_path, status="ok"))
                else:
                    result.folders.append(FolderResult(
                        path=folder_path,
                        status="error",
                        detail="folder not found",
                    ))
            except Exception as exc:
                result.folders.append(FolderResult(
                    path=folder_path,
                    status="error",
                    detail=str(exc),
                ))

        return result

    def list_expected_folders(self) -> List[str]:
        """Return the list of folder paths this vault should contain."""
        return self._folder_spec.all_folders

    def register_folders(self, folders: List[str]) -> None:
        """
        Add product-specific folders to the spec.

        Call before create_folders() to include custom folders.
        """
        self._folder_spec = self._folder_spec.extend(folders)

    # ------------------------------------------------------------------
    # File Operations
    # ------------------------------------------------------------------

    async def upload(
        self,
        subfolder: str,
        filename: str,
        content: bytes,
        mime_type: Optional[str] = None,
    ):
        """
        Upload a file to a vault subfolder.

        Args:
            subfolder: Relative to vault root, e.g. "documents", "certificates"
            filename:  Name of the file
            content:   File content as bytes
            mime_type: Optional MIME type
        """
        storage = self._get_storage()
        dest_path = f"{VAULT_ROOT}/{subfolder}"
        return await storage.upload_file(
            file_content=content,
            destination_path=dest_path,
            filename=filename,
            mime_type=mime_type,
        )

    async def download(self, subfolder: str, filename: str) -> bytes:
        """Download a file from a vault subfolder."""
        storage = self._get_storage()
        file_path = f"{VAULT_ROOT}/{subfolder}/{filename}"
        return await storage.download_file(file_path)

    async def list_files(self, subfolder: str):
        """List files in a vault subfolder."""
        storage = self._get_storage()
        folder_path = f"{VAULT_ROOT}/{subfolder}"
        return await storage.list_files(folder_path)

    async def delete(self, subfolder: str, filename: str) -> bool:
        """Delete a file from a vault subfolder."""
        storage = self._get_storage()
        file_path = f"{VAULT_ROOT}/{subfolder}/{filename}"
        return await storage.delete_file(file_path)

    # ------------------------------------------------------------------
    # Vault Lifecycle
    # ------------------------------------------------------------------

    async def health_check(self) -> HealthResult:
        """
        Check vault health: provider connectivity + folder existence.

        Returns a HealthResult with details about what exists and what's missing.
        """
        storage = self._get_storage()

        # Check provider connectivity
        try:
            connected = await storage.is_connected()
        except Exception:
            connected = False

        if not connected:
            return HealthResult(
                healthy=False,
                folders_exist=[],
                folders_missing=self._folder_spec.all_folders,
                provider_connected=False,
                detail="Cannot connect to storage provider",
            )

        # Check folders
        existing = []
        missing = []
        for folder_path in self._folder_spec.all_folders:
            try:
                files = await storage.list_files(folder_path)
                if files is not None:
                    existing.append(folder_path)
                else:
                    missing.append(folder_path)
            except Exception:
                missing.append(folder_path)

        return HealthResult(
            healthy=len(missing) == 0,
            folders_exist=existing,
            folders_missing=missing,
            provider_connected=True,
            detail=f"{len(existing)}/{len(self._folder_spec.all_folders)} folders present",
        )

    async def repair(self) -> VaultResult:
        """
        Repair a vault by creating any missing folders.

        Same as create_folders() but semantically indicates a repair operation.
        Safe to call on a healthy vault (no-op for existing folders).
        """
        return await self.create_folders()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def folder_spec(self) -> VaultFolderSpec:
        return self._folder_spec
