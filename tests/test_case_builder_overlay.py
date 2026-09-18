"""Tests for the CASE_DATA overlay-backed case storage migration.

These tests prove that case_builder.save_case() and create_case() write case
content to a CASE_DATA overlay in the user's cloud storage, and that the
INCIDENT overlay (post vault-persistence Phase 1) contains only the
case_overlay_id pointer and non-PII structure — no case number, names,
addresses, or narrative.
"""

from unittest.mock import patch

import pytest

from app.core.overlay_types import OverlayType, get_overlay_category
from app.core.user_context import StorageProvider, UserContext, UserRole
from app.services import incident_store
from app.services.unified_overlay_manager import UnifiedOverlayManager

# The package re-exports `router` (APIRouter), so import the module itself.
import importlib

cb_router = importlib.import_module("app.modules.case_builder.router")
load_case = cb_router.load_case
save_case = cb_router.save_case

# -----------------------------------------------------------------------------
# In-memory fake storage (mirrors the helper in tests/test_unified_overlay_manager)
# -----------------------------------------------------------------------------


class FakeStorageProvider:
    """In-memory cloud storage provider for overlay tests."""

    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.folders: set[str] = set()

    async def upload_file(self, file_content: bytes, destination_path: str, filename: str, mime_type: str = "") -> None:
        full_path = f"{destination_path}/{filename}"
        self.files[full_path] = file_content

    async def download_file(self, file_path: str) -> bytes | None:
        return self.files.get(file_path)

    async def create_folder(self, folder_path: str) -> bool:
        self.folders.add(folder_path)
        return True

    async def delete_file(self, file_path: str) -> bool:
        return bool(self.files.pop(file_path, None))

    async def file_exists(self, file_path: str) -> bool:
        return file_path in self.files

    async def list_files(self, folder_path: str = "/", recursive: bool = False) -> list:
        _ = folder_path, recursive
        return []


def _make_user(user_id: str) -> UserContext:
    return UserContext(
        user_id=user_id,
        provider=StorageProvider.GOOGLE_DRIVE,
        storage_user_id=f"drv_{user_id}",
        access_token="tok-test",
        role=UserRole.USER,
    )


@pytest.fixture
def vault_env(test_user_id, monkeypatch):
    """Wire incident_store + case_builder to a shared in-memory vault."""
    storage = FakeStorageProvider()
    user = _make_user(test_user_id)

    def fake_get_provider(provider_value: str, access_token: str | None = None):
        _ = provider_value, access_token
        return storage

    async def fake_ctx(user_id: str):
        return user

    monkeypatch.setattr(incident_store, "get_provider", fake_get_provider)
    monkeypatch.setattr(cb_router, "build_context_for_user_id", fake_ctx)
    case_manager = UnifiedOverlayManager(storage, test_user_id)
    return {"storage": storage, "user": user, "case_manager": case_manager}


@pytest.fixture
def case_data_with_pii():
    """A legacy-shaped case dict containing PII/case-management fields."""
    return {
        "case_number": "CV-2026-12345",
        "case_type": "eviction_defense",
        "court": "District Court - Hennepin County",
        "property_address": "123 Main St, Minneapolis, MN 55401",
        "rent_amount": 950.0,
        "security_deposit": 500.0,
        "plaintiff": {"name": "Acme Properties LLC", "role": "plaintiff"},
        "defendant": {"name": "Jane Doe", "role": "defendant", "is_pro_se": True},
        "hearing_date": "2026-07-20",
        "lease_start": "2026-01-01",
        "lease_end": "2026-12-31",
        "timeline": [
            {
                "date": "2026-06-10",
                "title": "Lease signed",
                "description": "Original lease signed.",
                "category": "lease",
                "importance": "high",
                "source": "document",
            },
        ],
        "evidence": [
            {"document_id": "doc-lease-1", "title": "Lease Agreement"},
        ],
        "counterclaims": [],
        "motions": [],
        "deadlines": [],
        "defenses": [],
        "notes": ["Possible retaliation pattern after repair request."],
        "duress_note": "Tenant felt pressured to sign lease addendum.",
    }


@pytest.mark.anyio
async def test_save_case_creates_case_data_overlay_and_clears_db(
    test_user_id, vault_env, case_data_with_pii
):
    """save_case() must write to a CASE_DATA overlay; the incident overlay
    keeps only the pointer + non-PII structure."""
    incident = await incident_store.create_incident(
        vault_env["user"],
        title="New case",
        status="draft",
        incident_type="eviction_defense",
        incident_metadata={},
    )
    case_id = str(incident.incident_id)

    with patch(
        "app.modules.case_builder.router._get_case_overlay_manager",
        return_value=vault_env["case_manager"],
    ):
        await save_case(case_id, case_data_with_pii, test_user_id)

    # The incident overlay holds pointer + non-PII tags only
    overlay = await incident_store.get_incident_overlay(vault_env["user"], int(case_id))
    p = overlay.payload
    assert p["case_overlay_id"] is not None
    assert p["case_overlay_id"].startswith("ovl_")
    assert not p["incident_metadata"]
    assert "CV-2026-12345" not in (p["title"] or "")
    assert "Acme" not in (p["title"] or "")
    assert "Jane" not in (p["title"] or "")
    assert "Main St" not in (p["title"] or "")

    with patch(
        "app.modules.case_builder.router._get_case_overlay_manager",
        return_value=vault_env["case_manager"],
    ):
        loaded = await load_case(case_id, test_user_id)

    assert loaded is not None
    assert loaded["case_id"] == case_id
    assert loaded["flag_category"] == "eviction_defense"
    assert loaded["narrative"] == "Possible retaliation pattern after repair request."
    assert len(loaded["timeline"]) == 1
    assert loaded["exhibit_refs"] == ["doc-lease-1"]
    assert loaded["flag_notes"].get("duress") == "Tenant felt pressured to sign lease addendum."
    # Case-management / PII fields must NOT be in the overlay payload
    assert "case_number" not in loaded
    assert "plaintiff" not in loaded
    assert "defendant" not in loaded
    assert "property_address" not in loaded
    assert "motions" not in loaded
    assert "deadlines" not in loaded


@pytest.mark.anyio
async def test_case_data_overlay_category_and_type(
    test_user_id, vault_env, case_data_with_pii
):
    """The overlay created by save_case() must be type CASE_DATA and category 'case'."""
    incident = await incident_store.create_incident(
        vault_env["user"],
        title="New case",
        status="draft",
        incident_type="eviction_defense",
        incident_metadata={},
    )
    case_id = str(incident.incident_id)

    with patch(
        "app.modules.case_builder.router._get_case_overlay_manager",
        return_value=vault_env["case_manager"],
    ):
        await save_case(case_id, case_data_with_pii, test_user_id)

    overlays = await vault_env["case_manager"].get_overlays(overlay_type=OverlayType.CASE_DATA)
    assert overlays.success is True
    assert overlays.count == 1
    overlay = overlays.overlays[0]
    assert overlay.overlay_type == OverlayType.CASE_DATA
    assert overlay.document_id == case_id
    assert get_overlay_category(overlay.overlay_type) == "case"


@pytest.mark.anyio
async def test_incident_integer_ids_allocate_per_user(test_user_id, vault_env):
    """incident_id stays an int and allocates max+1 per user — URL paths and
    VaultItem.related_incident_id links depend on it."""
    first = await incident_store.create_incident(vault_env["user"], title="a")
    second = await incident_store.create_incident(vault_env["user"], title="b")

    assert first.incident_id == 1
    assert second.incident_id == 2
    assert isinstance(first.incident_id, int)


@pytest.mark.anyio
async def test_incidents_isolated_per_user(test_user_id, vault_env, monkeypatch):
    """A second user's vault must not see the first user's incidents."""
    other_storage = FakeStorageProvider()
    other_user = _make_user("GUother999")

    await incident_store.create_incident(vault_env["user"], title="alice case")

    real_get_provider = incident_store.get_provider

    def multi_provider(provider_value: str, access_token: str | None = None):
        _ = provider_value, access_token
        return other_storage

    monkeypatch.setattr(incident_store, "get_provider", multi_provider)
    assert await incident_store.list_incidents(other_user) == []
    assert await incident_store.get_incident(other_user, 1) is None
