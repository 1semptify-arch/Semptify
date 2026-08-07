"""
External Vault Client — Phase 3.2a

Read/write vault files on behalf of an external module. Enforces
vault.read and vault.write permissions.

This is a thin wrapper around the internal VaultClient that injects the
external module's context for audit logging and permission checks.
"""
import logging

from app.sdk.external.context import ExternalModuleContext
from app.sdk.external.permissions import Permission
from app.sdk.vault import VaultClient as InternalVaultClient, VaultFolderSpec

logger = logging.getLogger(__name__)


class VaultClient:
    """External module vault access — enforces least privilege."""

    def __init__(
        self,
        ctx: ExternalModuleContext,
        provider: str,
        access_token: str,
        folder_spec: VaultFolderSpec,
    ):
        self._ctx = ctx
        self._provider = provider
        self._access_token = access_token
        self._folder_spec = folder_spec
        self._client = InternalVaultClient(
            provider=provider,
            access_token=access_token,
            user_id=ctx.user_id,
            folder_spec=folder_spec,
        )

    async def list_files(self, folder_path: str) -> list[dict]:
        """List files in a vault folder. Requires vault.read."""
        self._ctx.require_permission(Permission.VAULT_READ.value, "list_files")
        logger.info(
            "ExternalVault: module=%s vendor=%s list_files path=%s",
            self._ctx.module_name, self._ctx.vendor, folder_path,
        )
        return await self._client.list_files(folder_path)

    async def read_file(self, file_path: str) -> bytes:
        """Read a vault file. Requires vault.read."""
        self._ctx.require_permission(Permission.VAULT_READ.value, "read_file")
        logger.info(
            "ExternalVault: module=%s read_file path=%s",
            self._ctx.module_name, file_path,
        )
        return await self._client.read_file(file_path)

    async def upload_file(self, file_path: str, content: bytes) -> dict:
        """Upload a file to the vault. Requires vault.write."""
        self._ctx.require_permission(Permission.VAULT_WRITE.value, "upload_file")
        logger.info(
            "ExternalVault: module=%s upload_file path=%s size=%d",
            self._ctx.module_name, file_path, len(content),
        )
        return await self._client.upload_file(file_path, content)

    async def delete_file(self, file_path: str) -> bool:
        """Delete a vault file. Requires vault.write."""
        self._ctx.require_permission(Permission.VAULT_WRITE.value, "delete_file")
        logger.info(
            "ExternalVault: module=%s delete_file path=%s",
            self._ctx.module_name, file_path,
        )
        return await self._client.delete_file(file_path)
