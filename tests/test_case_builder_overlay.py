"""Tests for the CASE_DATA overlay-backed case storage migration.

These tests prove that case_builder.save_case() and create_case() write case
content to a CASE_DATA overlay in the user's cloud storage, and that the
Incident row in Postgres contains only the overlay pointer and non-PII
structure — no case number, names, addresses, or narrative.
"""

from unittest.mock import patch

import pytest

from app.core.overlay_types import OverlayType, get_overlay_category
from app.models.models import Incident
from app.modules.case_builder.router import load_case, save_case
from app.services.unified_overlay_manager import UnifiedOverlayManager

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


@pytest.fixture
def fake_case_manager(test_user_id):
    """Return a UnifiedOverlayManager backed by an in-memory fake storage."""
    storage = FakeStorageProvider()
    return UnifiedOverlayManager(storage, test_user_id)


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
    db_session,
    test_user_id,
    fake_case_manager,
    case_data_with_pii,
):
    """save_case() must write to a CASE_DATA overlay and keep DB free of PII."""
    incident = Incident(
        user_id=test_user_id,
        title="New case",
        status="draft",
        incident_type="eviction_defense",
        incident_metadata={},
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)
    case_id = str(incident.incident_id)

    with patch("app.modules.case_builder.router._get_case_overlay_manager", return_value=fake_case_manager):
        await save_case(case_id, case_data_with_pii, test_user_id)

    await db_session.refresh(incident)
    assert incident.case_overlay_id is not None
    assert incident.case_overlay_id.startswith("ovl_")
    assert not incident.incident_metadata
    assert "CV-2026-12345" not in (incident.title or "")
    assert "Acme" not in (incident.title or "")
    assert "Jane" not in (incident.title or "")
    assert "Main St" not in (incident.title or "")

    with patch("app.modules.case_builder.router._get_case_overlay_manager", return_value=fake_case_manager):
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
    db_session,
    test_user_id,
    fake_case_manager,
    case_data_with_pii,
):
    """The overlay created by save_case() must be type CASE_DATA and category 'case'."""
    incident = Incident(
        user_id=test_user_id,
        title="New case",
        status="draft",
        incident_type="eviction_defense",
        incident_metadata={},
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)
    case_id = str(incident.incident_id)

    with patch("app.modules.case_builder.router._get_case_overlay_manager", return_value=fake_case_manager):
        await save_case(case_id, case_data_with_pii, test_user_id)

    overlays = await fake_case_manager.get_overlays(overlay_type=OverlayType.CASE_DATA)
    assert overlays.success is True
    assert overlays.count == 1
    overlay = overlays.overlays[0]
    assert overlay.overlay_type == OverlayType.CASE_DATA
    assert overlay.document_id == case_id
    assert get_overlay_category(overlay.overlay_type) == "case"


@pytest.mark.anyio
async def test_create_case_endpoint_writes_overlay_not_db_metadata(
    authenticated_client,
    case_data_with_pii,
):
    """POST /api/case-builder/cases must create an Incident with no case data in Postgres."""
    case_create_payload = {
        "case_number": case_data_with_pii["case_number"],
        "case_type": case_data_with_pii["case_type"],
        "court": case_data_with_pii["court"],
        "property_address": case_data_with_pii["property_address"],
        "rent_amount": case_data_with_pii["rent_amount"],
        "security_deposit": case_data_with_pii["security_deposit"],
        "plaintiff_name": case_data_with_pii["plaintiff"]["name"],
        "defendant_name": case_data_with_pii["defendant"]["name"],
        "hearing_date": case_data_with_pii["hearing_date"],
        "lease_start": case_data_with_pii["lease_start"],
        "lease_end": case_data_with_pii["lease_end"],
        "notes": "Possible retaliation pattern after repair request.",
    }

    storage = FakeStorageProvider()
    manager = UnifiedOverlayManager(storage, "GUowner123")

    with patch("app.modules.case_builder.router._get_case_overlay_manager", return_value=manager):
        response = await authenticated_client.post("/api/case-builder/cases", json=case_create_payload)

    assert response.status_code == 200, response.text
    data = response.json()
    case_id = data["case_id"]
    assert case_id
    assert data["success"] is True

    from sqlalchemy import select

    from app.core.database import get_db_session

    async with get_db_session() as session:
        result = await session.execute(select(Incident).where(Incident.incident_id == int(case_id)))
        incident = result.scalar_one()
        assert incident.case_overlay_id is not None
        assert not incident.incident_metadata
        assert "CV-2026-12345" not in (incident.title or "")
        assert "Acme" not in (incident.title or "")
        assert "Jane" not in (incident.title or "")
        assert "Main St" not in (incident.title or "")

    # Verify the overlay exists and is readable
    overlays = await manager.get_overlays(overlay_type=OverlayType.CASE_DATA)
    assert overlays.success is True
    assert overlays.count == 1
    overlay = await manager.get_overlay(incident.case_overlay_id)
    assert overlay is not None
    assert overlay.payload["flag_category"] == "eviction_defense"
    assert "case_number" not in overlay.payload
    assert "plaintiff" not in overlay.payload
    assert "defendant" not in overlay.payload
    assert "property_address" not in overlay.payload
