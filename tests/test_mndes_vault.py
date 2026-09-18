"""Functional tests for MNDES exhibit-package overlays in the user vault."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.utc import utc_now
from app.models.mndes_exhibit import (
    MNDESAttestationRequest,
    MNDESCaseType,
    MNDESPackageCreateRequest,
    MNDESSubmissionConfirmRequest,
)
from app.modules.mndes import service as svc
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
def vault_env(monkeypatch):
    managers: dict[str, UnifiedOverlayManager] = {}
    users: dict[str, _FakeUser] = {}

    async def _manager(_storage, user_id):
        if user_id not in managers:
            managers[user_id] = UnifiedOverlayManager(FakeStorageProvider(), user_id)
        return managers[user_id]

    async def _ctx(user_id):
        return users.setdefault(user_id, _FakeUser(user_id))

    monkeypatch.setattr(svc, "build_context_for_user_id", _ctx)
    monkeypatch.setattr(svc, "get_provider", lambda *a, **k: object())
    monkeypatch.setattr(svc, "get_unified_overlay_manager", _manager)
    return managers


@pytest.fixture
def service():
    return svc.MNDESExhibitService()


@pytest.fixture
def create_request():
    return MNDESPackageCreateRequest(
        vault_ids=["doc-a", "doc-b"],
        mn_case_number="27-CV-24-999",
        case_type=MNDESCaseType.EVICTION,
        no_contact_order=False,
        is_sealed_case=False,
    )


@pytest.fixture
def vault_docs():
    return [
        {"vault_id": "doc-a", "filename": "lease.pdf", "file_size_bytes": 1024},
        {"vault_id": "doc-b", "filename": "notice.pdf", "file_size_bytes": 2048},
    ]


@pytest.mark.asyncio
async def test_create_and_get_round_trip(vault_env, service, create_request, vault_docs):
    package = await service.create_package(create_request, vault_docs, "user-1")

    fetched = await service.get_package(package.package_id, "user-1")
    assert fetched is not None
    assert fetched.package_id == package.package_id
    assert fetched.mn_case_number == "27-CV-24-999"
    assert len(fetched.exhibits) == 2


@pytest.mark.asyncio
async def test_attestation_persists_through_vault(vault_env, service, create_request, vault_docs):
    package = await service.create_package(create_request, vault_docs, "user-1")

    updated = await service.apply_attestations(
        MNDESAttestationRequest(
            package_id=package.package_id,
            attests_no_sexual_content=True,
            attests_not_discovery=True,
            attests_not_motion_attachment=True,
            attests_understands_no_return=True,
            attests_semptify_not_mndes=True,
        ),
        "user-1",
    )
    assert updated.checklist_complete is True

    # Re-read through a fresh service (no in-memory cache carry-over matters less
    # than the overlay update) — payload must reflect the update, not the create.
    fetched = await service._get_package_from_vault(package.package_id, "user-1")
    assert fetched.checklist_complete is True


@pytest.mark.asyncio
async def test_confirm_submission_updates_status(vault_env, service, create_request, vault_docs):
    package = await service.create_package(create_request, vault_docs, "user-1")

    for ex in package.exhibits:
        package = await service.confirm_submission(
            MNDESSubmissionConfirmRequest(
                package_id=package.package_id,
                exhibit_id=ex.exhibit_id,
                mndes_tracking_number="MN-1",
            ),
            "user-1",
        )
    assert package.mndes_submission_complete is True

    fetched = await service._get_package_from_vault(package.package_id, "user-1")
    assert fetched.mndes_submission_complete is True


@pytest.mark.asyncio
async def test_per_user_isolation(vault_env, service, create_request, vault_docs):
    package = await service.create_package(create_request, vault_docs, "user-1")

    # Another user's vault has no such package (and no legacy import for them)
    assert await service._get_package_from_vault(package.package_id, "user-2") is None


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _FakeDB:
    def __init__(self, rows_by_model):
        self._rows_by_model = rows_by_model

    async def execute(self, query):
        model_name = str(query)
        for name, rows in self._rows_by_model.items():
            if name in model_name:
                return _FakeResult(rows)
        return _FakeResult([])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def _legacy_row(**fields):
    row = SimpleNamespace(**fields)
    row.__table__ = SimpleNamespace(columns=[SimpleNamespace(name=k) for k in fields])
    return row


def _package_row(user_id="user-1", package_id="pkg-legacy-1", **overrides):
    now = utc_now()
    fields = dict(
        id=7,
        package_id=package_id,
        user_id=user_id,
        mn_case_number="27-CV-24-555",
        case_type="eviction",
        case_caption="LL v. Tenant",
        package_name="Package for 27-CV-24-555",
        description=None,
        exhibits_json="[]",
        requires_attestation=True,
        attestation_provided=False,
        attestation_date=None,
        attested_by=None,
        status="draft",
        is_sealed_case=False,
        submitted_at=None,
        confirmation_number=None,
        created_at=now,
        updated_at=now,
    )
    fields.update(overrides)
    return _legacy_row(**fields)


@pytest.mark.asyncio
async def test_legacy_migration_bounded_and_idempotent(vault_env, service, monkeypatch):
    rows = {"mndes_exhibit_packages": [_package_row()]}
    monkeypatch.setattr(svc, "get_db_session", lambda: _FakeDB(rows))

    assert await service._migrate_legacy_packages("user-1") == 1
    assert await service._migrate_legacy_packages("user-1") == 0

    fetched = await service._get_package_from_vault("pkg-legacy-1", "user-1")
    assert fetched is not None
    assert fetched.mn_case_number == "27-CV-24-555"
    assert fetched.case_caption == "LL v. Tenant"


@pytest.mark.asyncio
async def test_get_package_imports_legacy_row_on_access(vault_env, service, monkeypatch):
    rows = {"mndes_exhibit_packages": [_package_row(package_id="pkg-legacy-2")]}
    monkeypatch.setattr(svc, "get_db_session", lambda: _FakeDB(rows))

    fetched = await service.get_package("pkg-legacy-2", "user-1")
    assert fetched is not None
    assert fetched.package_id == "pkg-legacy-2"

    # Row was imported into the vault — present without hitting the DB path
    vault_fetched = await service._get_package_from_vault("pkg-legacy-2", "user-1")
    assert vault_fetched is not None

    # Cross-user access does not leak the package — the legacy DB fallback
    # guards on package.user_id (fake DB can't apply WHERE, so isolate the
    # ownership check from the migration path).
    monkeypatch.setattr(service, "_migrate_legacy_packages", AsyncMock(return_value=0))
    assert await service.get_package("pkg-legacy-2", "user-2") is None
