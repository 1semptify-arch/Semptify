import json

import pytest

from app.services.storage.vault_manager import (
    AUTH_FOLDER,
    PROVISIONING_FILE,
    TOKEN_BACKUP,
    TOKEN_FILE,
    VaultManager,
)


class FakeStorageProvider:
    def __init__(self):
        self.folders = set()
        self.files = {}

    async def create_folder(self, path: str):
        self.folders.add(path)

    async def upload_file(self, file_content, destination_path: str, filename: str, mime_type: str):
        full_path = f"{destination_path}/{filename}" if destination_path else filename
        self.files[full_path] = file_content

    async def download_file(self, path: str):
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]


class CorruptBackupStorageProvider(FakeStorageProvider):
    async def upload_file(self, file_content, destination_path: str, filename: str, mime_type: str):
        full_path = f"{destination_path}/{filename}" if destination_path else filename
        if filename == "token.enc.backup":
            self.files[full_path] = b"corrupt-bytes"
            return
        self.files[full_path] = file_content


@pytest.mark.anyio
async def test_initialize_vault_sets_enabled_only_after_verification():
    storage = FakeStorageProvider()
    manager = VaultManager(storage, "GUabc12345", "http://localhost:8000")

    result = await manager.initialize_vault(
        provider_name="google_drive",
        access_token="access-token",
        refresh_token="refresh-token",
        token_expires_at="2030-01-01T00:00:00Z",
    )

    assert result["success"] is True
    assert result["vault_created"] is True
    assert result["vault_enabled"] is True
    assert TOKEN_FILE in storage.files
    assert TOKEN_BACKUP in storage.files

    state = json.loads(storage.files[PROVISIONING_FILE].decode())
    assert state["state"] == "enabled"
    assert state["vault_created"] is True
    assert state["vault_enabled"] is True


@pytest.mark.anyio
async def test_initialize_vault_marks_failed_when_token_verification_fails():
    storage = CorruptBackupStorageProvider()
    manager = VaultManager(storage, "GUabc12345", "http://localhost:8000")

    with pytest.raises(Exception):
        await manager.initialize_vault(
            provider_name="google_drive",
            access_token="access-token",
            refresh_token="refresh-token",
            token_expires_at="2030-01-01T00:00:00Z",
        )

    state = json.loads(storage.files[PROVISIONING_FILE].decode())
    assert state["state"] == "failed"
    assert state["vault_created"] is True
    assert state["vault_enabled"] is False
