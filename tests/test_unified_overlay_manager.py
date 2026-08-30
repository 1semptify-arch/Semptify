"""Targeted tests for app.services.unified_overlay_manager.

These tests cover the core overlay lifecycle (create, read, update, delete,
query, compose view) with a fake in-memory storage provider. They are
intentionally scoped to the public methods of UnifiedOverlayManager and the
error/retry paths that are independent of a real cloud backend.
"""

import json

import pytest

from app.core.overlay_types import OverlayType
from app.core.utc import utc_now
from app.core.vault_paths import VAULT_OVERLAY_DOCUMENTS, VAULT_OVERLAY_REGISTRY
from app.models.unified_overlay_models import CreateOverlayRequest
from app.services.storage.base import StorageFile, StorageProvider
from app.services.unified_overlay_manager import UnifiedOverlayManager


class FakeStorageProvider(StorageProvider):
    """In-memory storage provider for unit-testing overlay operations."""

    def __init__(self):
        super().__init__()
        self.files: dict[str, bytes] = {}
        self.folders: set[str] = set()

    @property
    def provider_name(self) -> str:
        return "fake"

    async def is_connected(self) -> bool:
        return True

    async def upload_file(
        self,
        file_content: bytes,
        destination_path: str,
        filename: str,
        mime_type: str | None = None,
    ) -> StorageFile:
        path = f"{destination_path}/{filename}"
        self.files[path] = file_content
        return StorageFile(
            id=filename,
            name=filename,
            path=path,
            size=len(file_content),
            mime_type=mime_type or "application/json",
            modified_at=utc_now(),
        )

    async def download_file(self, file_path: str) -> bytes:
        return self.files.get(file_path, b"")

    async def delete_file(self, file_path: str) -> bool:
        return bool(self.files.pop(file_path, None))

    async def list_files(self, folder_path: str = "/", recursive: bool = False) -> list:
        _ = folder_path, recursive
        return []

    async def file_exists(self, file_path: str) -> bool:
        return file_path in self.files

    async def create_folder(self, folder_path: str) -> bool:
        self.folders.add(folder_path)
        return True


@pytest.fixture
def fake_storage():
    return FakeStorageProvider()


@pytest.fixture
def sample_overlay_request() -> CreateOverlayRequest:
    return CreateOverlayRequest(
        overlay_type=OverlayType.HIGHLIGHT,
        document_id="doc-1",
        vault_path="Semptify5.0/Vault/documents/lease.pdf",
        payload={"color": "yellow", "range": {"start_offset": 10, "end_offset": 20}},
        metadata={"jurisdiction": "MN"},
        ephemeral=False,
    )


@pytest.mark.anyio
async def test_create_overlay_persists_and_updates_registry(
    fake_storage: FakeStorageProvider,
    sample_overlay_request: CreateOverlayRequest,
):
    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")
    response = await manager.create_overlay(sample_overlay_request)

    assert response.success is True
    assert response.overlay_id
    assert response.overlay_type == OverlayType.HIGHLIGHT

    overlay_path = f"{VAULT_OVERLAY_DOCUMENTS}/{response.overlay_id}.json"
    assert overlay_path in fake_storage.files

    registry_raw = fake_storage.files.get(VAULT_OVERLAY_REGISTRY, b"")
    assert registry_raw
    registry = json.loads(registry_raw.decode("utf-8"))
    assert response.overlay_id in registry
    assert registry[response.overlay_id]["overlay_type"] == "highlight"
    assert registry[response.overlay_id]["document_id"] == "doc-1"


@pytest.mark.anyio
async def test_create_ephemeral_overlay_is_not_persisted(
    fake_storage: FakeStorageProvider,
):
    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")
    request = CreateOverlayRequest(
        overlay_type=OverlayType.WATERMARKED_VIEW,
        document_id="doc-1",
        vault_path="Semptify5.0/Vault/documents/lease.pdf",
        payload={"watermark": "preview"},
        ephemeral=True,
    )
    response = await manager.create_overlay(request)

    assert response.success is True
    assert "not persisted" in response.message
    overlay_path = f"{VAULT_OVERLAY_DOCUMENTS}/{response.overlay_id}.json"
    assert overlay_path not in fake_storage.files
    assert VAULT_OVERLAY_REGISTRY not in fake_storage.files


@pytest.mark.anyio
async def test_create_overlay_chains_previous_overlay_hash(
    fake_storage: FakeStorageProvider,
    sample_overlay_request: CreateOverlayRequest,
):
    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")

    first = await manager.create_overlay(sample_overlay_request)
    assert first.success

    second_request = CreateOverlayRequest(
        overlay_type=OverlayType.NOTE,
        document_id=sample_overlay_request.document_id,
        vault_path=sample_overlay_request.vault_path,
        payload={"content": "Follow-up note"},
    )
    second = await manager.create_overlay(second_request)
    assert second.success

    first_data = json.loads(fake_storage.files[f"{VAULT_OVERLAY_DOCUMENTS}/{first.overlay_id}.json"].decode())
    second_data = json.loads(fake_storage.files[f"{VAULT_OVERLAY_DOCUMENTS}/{second.overlay_id}.json"].decode())
    assert second_data["prev_overlay_hash"] == first_data["overlay_hash"]


@pytest.mark.anyio
async def test_get_overlays_filters_and_returns_metadata(
    fake_storage: FakeStorageProvider,
    sample_overlay_request: CreateOverlayRequest,
):
    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")

    await manager.create_overlay(sample_overlay_request)
    await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.NOTE,
            document_id="doc-2",
            vault_path="Semptify5.0/Vault/documents/notice.pdf",
            payload={"content": "unrelated"},
        )
    )

    query = await manager.get_overlays(document_id="doc-1")
    assert query.success is True
    assert query.count == 1
    assert query.overlays[0].document_id == "doc-1"
    assert query.filters_applied["document_id"] == "doc-1"

    by_type = await manager.get_overlays(overlay_type=OverlayType.HIGHLIGHT)
    assert by_type.count == 1
    assert by_type.overlays[0].overlay_type == OverlayType.HIGHLIGHT

    by_category = await manager.get_overlays(category="annotation")
    assert by_category.count == 2
    assert all(o.get_category() == "annotation" for o in by_category.overlays)


@pytest.mark.anyio
async def test_get_overlays_skips_malformed_registry_entries(
    fake_storage: FakeStorageProvider,
):
    fake_storage.files[VAULT_OVERLAY_REGISTRY] = json.dumps({
        "good-1": {
            "overlay_id": "good-1",
            "overlay_type": "highlight",
            "document_id": "doc-1",
            "vault_path": "Semptify5.0/Vault/documents/lease.pdf",
            "created_by": "GUtest1234",
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
            "payload": {},
            "metadata": {},
            "ephemeral": False,
            "version": "1.0",
        },
        "bad-1": "not a dict",
        "bad-2": {"overlay_type": "invalid_type_value"},
    }, default=str).encode("utf-8")

    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")
    query = await manager.get_overlays()
    assert query.count == 1
    assert query.overlays[0].overlay_id == "good-1"


@pytest.mark.anyio
async def test_get_overlay_by_id_round_trip(
    fake_storage: FakeStorageProvider,
    sample_overlay_request: CreateOverlayRequest,
):
    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")
    created = await manager.create_overlay(sample_overlay_request)

    fetched = await manager.get_overlay(created.overlay_id)
    assert fetched is not None
    assert fetched.overlay_id == created.overlay_id
    assert fetched.payload == sample_overlay_request.payload

    missing = await manager.get_overlay("does-not-exist")
    assert missing is None


@pytest.mark.anyio
async def test_update_overlay_mutates_payload_and_metadata(
    fake_storage: FakeStorageProvider,
    sample_overlay_request: CreateOverlayRequest,
):
    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")
    created = await manager.create_overlay(sample_overlay_request)
    original = await manager.get_overlay(created.overlay_id)

    ok = await manager.update_overlay(
        created.overlay_id,
        payload={"color": "green"},
        metadata={"reviewed": True},
    )
    assert ok is True

    updated = await manager.get_overlay(created.overlay_id)
    assert updated.payload["color"] == "green"
    assert updated.metadata["reviewed"] is True
    assert updated.overlay_hash != original.overlay_hash
    assert updated.updated_at >= original.updated_at


@pytest.mark.anyio
async def test_update_overlay_enforces_ownership(
    fake_storage: FakeStorageProvider,
    sample_overlay_request: CreateOverlayRequest,
):
    owner_manager = UnifiedOverlayManager(fake_storage, "GUowner123")
    created = await owner_manager.create_overlay(sample_overlay_request)

    other_manager = UnifiedOverlayManager(fake_storage, "GUother456")
    ok = await other_manager.update_overlay(created.overlay_id, payload={"color": "red"})
    assert ok is False


@pytest.mark.anyio
async def test_delete_overlay_removes_file_and_registry(
    fake_storage: FakeStorageProvider,
    sample_overlay_request: CreateOverlayRequest,
):
    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")
    created = await manager.create_overlay(sample_overlay_request)
    overlay_path = f"{VAULT_OVERLAY_DOCUMENTS}/{created.overlay_id}.json"

    ok = await manager.delete_overlay(created.overlay_id)
    assert ok is True
    assert overlay_path not in fake_storage.files

    registry = json.loads(fake_storage.files[VAULT_OVERLAY_REGISTRY].decode("utf-8"))
    assert created.overlay_id not in registry

    missing = await manager.get_overlay(created.overlay_id)
    assert missing is None


@pytest.mark.anyio
async def test_delete_overlay_enforces_ownership(
    fake_storage: FakeStorageProvider,
    sample_overlay_request: CreateOverlayRequest,
):
    owner = UnifiedOverlayManager(fake_storage, "GUowner123")
    created = await owner.create_overlay(sample_overlay_request)

    other = UnifiedOverlayManager(fake_storage, "GUother456")
    ok = await other.delete_overlay(created.overlay_id)
    assert ok is False

    overlay_path = f"{VAULT_OVERLAY_DOCUMENTS}/{created.overlay_id}.json"
    assert overlay_path in fake_storage.files


@pytest.mark.anyio
async def test_compose_document_view_filters_by_document_id(
    fake_storage: FakeStorageProvider,
    sample_overlay_request: CreateOverlayRequest,
):
    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")

    highlight = await manager.create_overlay(sample_overlay_request)
    other = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.NOTE,
            document_id="doc-2",
            vault_path="Semptify5.0/Vault/documents/other.pdf",
            payload={"content": "other"},
        )
    )

    response = await manager.compose_document_view(
        "doc-1",
        [highlight.overlay_id, other.overlay_id],
    )
    assert response.success is True
    assert other.overlay_id not in response.applied_overlays
    assert highlight.overlay_id in response.applied_overlays


@pytest.mark.anyio
async def test_compose_document_view_sorts_redactions_last(
    fake_storage: FakeStorageProvider,
):
    manager = UnifiedOverlayManager(fake_storage, "GUtest1234")

    note = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.NOTE,
            document_id="doc-1",
            vault_path="Semptify5.0/Vault/documents/lease.pdf",
            payload={"content": "note"},
        )
    )
    redaction = await manager.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType.PII_REDACTION,
            document_id="doc-1",
            vault_path="Semptify5.0/Vault/documents/lease.pdf",
            payload={"ranges": []},
        )
    )

    response = await manager.compose_document_view(
        "doc-1",
        [redaction.overlay_id, note.overlay_id],
        apply_redactions=True,
    )
    assert response.success is True
    assert response.applied_overlays[-1] == redaction.overlay_id
