from unittest.mock import AsyncMock

import pytest

from app.sdk.vault import TENANT_VAULT, VaultClient


class FakeStorageProvider:
    def __init__(self, exists_map):
        self.exists_map = exists_map
        self.file_exists = AsyncMock(side_effect=self._file_exists)

    async def _file_exists(self, path: str) -> bool:
        return self.exists_map.get(path, False)


@pytest.mark.anyio
async def test_vault_client_verify_folders_uses_file_exists(monkeypatch):
    storage = FakeStorageProvider(exists_map=dict.fromkeys(TENANT_VAULT.all_folders, True))

    def fake_get_provider(provider_name: str, access_token: str):
        return storage

    monkeypatch.setattr("app.services.storage.get_provider", fake_get_provider)

    client = VaultClient(
        provider="google_drive",
        access_token="mock-access-token",
        user_id="GUtest1234",
        folder_spec=TENANT_VAULT,
    )

    result = await client.verify_folders()

    assert result.all_ok is True
    assert len(result.folders) == len(TENANT_VAULT.all_folders)
    storage.file_exists.assert_awaited()


@pytest.mark.anyio
async def test_vault_client_verify_folders_reports_missing_folder(monkeypatch):
    all_folders = list(TENANT_VAULT.all_folders)
    missing_folder = all_folders[0]
    exists_map = {folder: folder != missing_folder for folder in all_folders}
    storage = FakeStorageProvider(exists_map=exists_map)

    def fake_get_provider(provider_name: str, access_token: str):
        return storage

    monkeypatch.setattr("app.services.storage.get_provider", fake_get_provider)

    client = VaultClient(
        provider="google_drive",
        access_token="mock-access-token",
        user_id="GUtest1234",
        folder_spec=TENANT_VAULT,
    )

    result = await client.verify_folders()

    assert result.all_ok is False
    assert any(folder.path == missing_folder and folder.status == "error" for folder in result.folders)
    assert any(folder.path != missing_folder and folder.status == "ok" for folder in result.folders)
    storage.file_exists.assert_awaited()
