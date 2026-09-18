"""Functional tests for external-mapping overlays in the user vault."""

from types import SimpleNamespace

import pytest

from app.core.utc import utc_now
from app.services import external_mapping_store as store
from app.services.unified_overlay_manager import UnifiedOverlayManager
from tests.test_unified_overlay_manager import FakeStorageProvider


class _FakeUser:
    provider = type("P", (), {"value": "google_drive"})()

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.access_token = "token"

    def get_effective_user_id(self):
        return self.user_id


@pytest.fixture
def store_env(monkeypatch):
    managers: dict[str, UnifiedOverlayManager] = {}

    async def _manager(_storage, user_id):
        if user_id not in managers:
            managers[user_id] = UnifiedOverlayManager(FakeStorageProvider(), user_id)
        return managers[user_id]

    monkeypatch.setattr(store, "get_provider", lambda *a, **k: object())
    monkeypatch.setattr(store, "get_unified_overlay_manager", _manager)
    return managers


@pytest.mark.asyncio
async def test_general_mapping_crud(store_env):
    user = _FakeUser("user-1")

    m = await store.create_mapping(
        user,
        mapping_type="court_case",
        external_system="mn_courts",
        external_id="27-CV-24-123",
        display_name="Eviction case",
        verification_source="user_input",
    )
    assert m.id == 1
    assert m.verified is True
    assert m.to_dict()["septify_entity_type"] is None  # legacy key spelling preserved

    # Dedupe lookup
    found = await store.find_by_external_id(user, "mn_courts", "27-CV-24-123", "court_case")
    assert found.id == m.id

    # Status update
    updated = await store.update_mapping_status(user, m.id, "resolved", "admin_review")
    assert updated.status == "resolved"
    assert updated.verification_source == "admin_review"

    # List honors status filter (resolved no longer "active")
    assert await store.list_mappings(user, status="active") == []
    resolved = await store.list_mappings(user, status="resolved")
    assert len(resolved) == 1

    # Get by int id
    assert (await store.get_mapping(user, m.id)).id == m.id


@pytest.mark.asyncio
async def test_all_four_kinds_and_isolation(store_env):
    user = _FakeUser("user-2")

    case = await store.create_court_case(
        user, court_system="mn_state", case_number="EV-99", case_type="eviction", plaintiff="LL", defendant="T"
    )
    prop = await store.create_property(
        user, parcel_id="P-1", county="hennepin", street_address="1 Main St", city="Minneapolis", zip_code="55401"
    )
    agency = await store.create_agency_mapping(
        user, agency_code="hud", agency_name="HUD", complaint_number="C-7",
        complaint_type="discrimination", semptify_complaint_id="cmp-1",
    )

    # Per-kind int ids each start at 1
    assert (case.id, prop.id, agency.id) == (1, 1, 1)

    # Dedupe helpers
    assert await store.find_court_case(user, "EV-99", "mn_state") is not None
    assert await store.find_property(user, "P-1", "hennepin") is not None
    assert await store.find_agency_mapping(user, "hud", "C-7") is not None
    assert await store.find_court_case(user, "EV-99", "federal") is None

    # Isolation
    other = _FakeUser("user-other")
    assert await store.list_court_cases(other) == []
    assert await store.list_properties(other) == []
    assert await store.list_agency_mappings(other) == []


@pytest.mark.asyncio
async def test_list_filters(store_env):
    user = _FakeUser("user-3")
    await store.create_court_case(user, court_system="mn_state", case_number="A1", case_type="eviction")
    await store.create_court_case(
        user, court_system="mn_state", case_number="A2", case_type="housing", case_status="settled"
    )
    await store.create_property(
        user, parcel_id="P1", county="hennepin", street_address="1 A St", city="Mpls", zip_code="55401"
    )
    await store.create_property(
        user, parcel_id="P2", county="ramsey", street_address="2 B St", city="StP", zip_code="55101",
        is_primary_residence=False,
    )

    assert len(await store.list_court_cases(user, case_type="eviction")) == 1
    assert len(await store.list_court_cases(user, case_status="settled")) == 1
    assert len(await store.list_properties(user, county="ramsey")) == 1
    assert len(await store.list_properties(user, is_primary=True)) == 1


@pytest.mark.asyncio
async def test_search_across_kinds(store_env):
    user = _FakeUser("user-4")
    await store.create_mapping(user, mapping_type="attorney", external_system="mn_bar", external_id="BAR-12345")
    await store.create_court_case(user, court_system="mn_state", case_number="27-CV-12345", case_type="eviction")
    await store.create_property(
        user, parcel_id="PX", county="dakota", street_address="9 Oak Ln", city="Burnsville", zip_code="55306"
    )
    await store.create_agency_mapping(
        user, agency_code="mn_ag", agency_name="MN AG", complaint_number="AG-12345",
        complaint_type="habitability", semptify_complaint_id="cmp-2",
    )

    results = await store.search(user, "12345")
    assert len(results["general_mappings"]) == 1
    assert len(results["court_cases"]) == 1
    assert len(results["agencies"]) == 1
    assert len(results["properties"]) == 0

    # Case-insensitive + field coverage
    results = await store.search(user, "oak")
    assert len(results["properties"]) == 1

    # mapping_type filter applies to general mappings only
    results = await store.search(user, "12345", mapping_type="attorney")
    assert len(results["general_mappings"]) == 1


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows_by_model):
        self._rows_by_model = rows_by_model

    async def execute(self, query):
        # Resolve which model the select() targets via its column descriptions
        model_name = str(query)
        for name, rows in self._rows_by_model.items():
            if name in model_name:
                return _FakeResult(rows)
        return _FakeResult([])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def _row(model_fields):
    return SimpleNamespace(**model_fields)


@pytest.mark.asyncio
async def test_migrate_legacy_mappings_idempotent(store_env, monkeypatch):
    import app.core.database as database_mod

    user = _FakeUser("user-5")
    now = utc_now()
    rows = {
        "external_mappings": [
            _row(dict(id=11, user_id="user-5", mapping_type="attorney", external_system="mn_bar",
                      external_id="B-1", external_url=None, semptify_entity_type=None,
                      semptify_entity_id=None, display_name="Atty", description=None,
                      status="active", verified=True, verification_source="x",
                      created_at=now, updated_at=now)),
        ],
        "court_case_mappings": [
            _row(dict(id=22, user_id="user-5", court_system="mn_state", case_number="EV-1",
                      case_type="eviction", case_title=None, court_name=None, judge_name=None,
                      division=None, plaintiff="LL", defendant="T", attorney_bar_numbers=None,
                      filing_date=None, hearing_date=None, trial_date=None, case_status="active",
                      case_portal_url=None, document_filing_url=None, semptify_complaint_id=None,
                      semptify_timeline_event_ids=None, created_at=now, updated_at=now)),
        ],
        "property_mappings": [
            _row(dict(id=33, user_id="user-5", parcel_id="PL-9", county="ramsey", municipality=None,
                      street_address="5 Elm", unit=None, city="StP", state="MN", zip_code="55101",
                      property_type=None, tax_id=None, county_assessor_url=None,
                      county_recorder_url=None, gis_map_url=None, semptify_lease_doc_id=None,
                      is_primary_residence=True, verified=False, created_at=now, updated_at=now)),
        ],
        "agency_mappings": [
            _row(dict(id=44, user_id="user-5", agency_code="hud", agency_name="HUD",
                      complaint_number="HD-3", complaint_type="discrimination",
                      submission_date=None, submission_method=None, complaint_status="submitted",
                      resolution_date=None, resolution_outcome=None, agency_portal_url=None,
                      tracking_url=None, semptify_complaint_id="cmp-9",
                      semptify_document_ids=None, created_at=now, updated_at=now)),
        ],
    }
    monkeypatch.setattr(database_mod, "get_db_session", lambda: _FakeDB(rows))

    imported_first = await store.migrate_legacy_mappings(user)
    imported_second = await store.migrate_legacy_mappings(user)

    assert imported_first == 4
    assert imported_second == 0

    # Integer PKs preserved per kind
    assert (await store.get_mapping(user, 11)).display_name == "Atty"
    assert (await store.find_court_case(user, "EV-1", "mn_state")).id == 22
    assert (await store.find_property(user, "PL-9", "ramsey")).id == 33
    assert (await store.find_agency_mapping(user, "hud", "HD-3")).id == 44


@pytest.mark.asyncio
async def test_migrate_legacy_mappings_safe_without_db(store_env):
    user = _FakeUser("user-6")
    assert await store.migrate_legacy_mappings(user) == 0
