"""Vault-resident per-role configs — payloads + remote install (Step 1d)."""

import json
from unittest.mock import AsyncMock

import pytest

from app.core.vault_configs import (
    DOC_TYPE_FIELDS,
    OCR_CONFIG_VERSION,
    OVERLAY_CONFIG_VERSION,
    configs_for_role,
    ocr_config_for_role,
    overlay_config_for_role,
)
from app.core.vault_paths import CONFIGS_FOLDER, OCR_CONFIG_FILE, OVERLAY_CONFIG_FILE
from app.sdk.vault import configs as vault_configs


class FakeStorageProvider:
    """Dict-backed storage — files keyed by full path."""

    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.uploads = 0

    async def file_exists(self, path: str) -> bool:
        return path in self.files

    async def download_file(self, path: str) -> bytes:
        return self.files[path]

    async def upload_file(self, file_content, destination_path, filename, mime_type=None):
        self.files[f"{destination_path}/{filename}"] = file_content
        self.uploads += 1
        return None

    async def delete_file(self, path: str) -> bool:
        return self.files.pop(path, None) is not None

    async def create_folder(self, path: str) -> bool:
        return True


# ---------------------------------------------------------------------------
# Payload shape
# ---------------------------------------------------------------------------

def test_ocr_config_covers_all_eight_doc_types_for_tenant():
    cfg = ocr_config_for_role("tenant")
    assert set(cfg["doc_types"]) == set(DOC_TYPE_FIELDS)
    assert cfg["text_layer_first"] is True
    assert cfg["engine"]["primary"] == "client_wasm_onnx"
    assert cfg["engine"]["fallback"] == "server_ephemeral"
    assert cfg["engine"]["content_logging"] == "none"
    assert cfg["confirm_flow"]["controls"] == ["yes", "no", "edit"]
    assert cfg["confirm_flow"]["all_confirmed_state"] == "verified"


def test_ocr_config_empty_doc_types_for_non_intake_roles():
    for role in ("donor_supporter", "judge", "researcher", None, "bogus"):
        assert ocr_config_for_role(role)["doc_types"] == {}


def test_overlay_config_categories_per_role():
    tenant = overlay_config_for_role("tenant")["allowed_categories"]
    assert {"annotation", "record", "upload"} <= set(tenant)
    assert "identity" not in tenant  # tenants never view-as
    assert "identity" in overlay_config_for_role("advocate")["allowed_categories"]
    assert overlay_config_for_role("donor_supporter")["allowed_categories"] == []
    assert overlay_config_for_role(None)["allowed_categories"] == []


def test_configs_keyed_by_remote_path():
    files = configs_for_role("tenant")
    assert set(files) == {OCR_CONFIG_FILE, OVERLAY_CONFIG_FILE}
    assert all(path.startswith(CONFIGS_FOLDER) for path in files)


def test_payloads_are_json_serializable():
    for role in ("tenant", "legal", "donor_supporter", None):
        for payload in configs_for_role(role).values():
            json.dumps(payload)  # must not raise


# ---------------------------------------------------------------------------
# Remote install
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_ensure_configs_creates_both_files():
    storage = FakeStorageProvider()
    result = await vault_configs.ensure_configs_remote(storage, "tenant")
    assert result["success"] is True
    assert result["files"][OCR_CONFIG_FILE] == "created"
    assert result["files"][OVERLAY_CONFIG_FILE] == "created"
    expected = {OCR_CONFIG_FILE: OCR_CONFIG_VERSION, OVERLAY_CONFIG_FILE: OVERLAY_CONFIG_VERSION}
    for path, version in expected.items():
        payload = json.loads(storage.files[path].decode("utf-8"))
        assert payload["version"] == version
        assert payload["role"] == "tenant"


@pytest.mark.anyio
async def test_ensure_configs_idempotent_verified():
    storage = FakeStorageProvider()
    await vault_configs.ensure_configs_remote(storage, "tenant")
    uploads = storage.uploads
    result = await vault_configs.ensure_configs_remote(storage, "advocate")
    assert set(result["files"].values()) == {"verified"}
    assert storage.uploads == uploads  # no writes on re-run


@pytest.mark.anyio
async def test_ensure_configs_refreshes_stale_version():
    storage = FakeStorageProvider()
    storage.files[OCR_CONFIG_FILE] = json.dumps(
        {"version": 0, "role": "tenant"}
    ).encode("utf-8")
    result = await vault_configs.ensure_configs_remote(storage, "tenant")
    assert result["files"][OCR_CONFIG_FILE] == "refreshed"
    assert json.loads(storage.files[OCR_CONFIG_FILE])["version"] == OCR_CONFIG_VERSION


@pytest.mark.anyio
async def test_ensure_configs_replaces_unparseable():
    storage = FakeStorageProvider()
    storage.files[OVERLAY_CONFIG_FILE] = b"\x00\xff not json"
    result = await vault_configs.ensure_configs_remote(storage, "tenant")
    assert result["files"][OVERLAY_CONFIG_FILE] == "refreshed"
    assert json.loads(storage.files[OVERLAY_CONFIG_FILE])["version"] == OVERLAY_CONFIG_VERSION


@pytest.mark.anyio
async def test_ensure_configs_never_downgrades_newer():
    storage = FakeStorageProvider()
    future = json.dumps({"version": 99, "role": "tenant"}).encode("utf-8")
    storage.files[OCR_CONFIG_FILE] = future
    result = await vault_configs.ensure_configs_remote(storage, "tenant")
    assert result["files"][OCR_CONFIG_FILE] == "kept_newer"
    assert storage.files[OCR_CONFIG_FILE] == future
