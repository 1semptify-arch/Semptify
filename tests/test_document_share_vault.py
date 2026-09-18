"""Functional tests for document-share overlays in the owner's vault."""

from types import SimpleNamespace

import pytest

from app.core.utc import utc_now
from app.services import document_share_store
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

    monkeypatch.setattr(document_share_store, "get_provider", lambda *a, **k: object())
    monkeypatch.setattr(document_share_store, "get_unified_overlay_manager", _manager)
    return managers


def _patch_ctx(monkeypatch):
    """build_context_for_user_id resolves to a _FakeUser for token resolution."""
    async def _ctx(user_id):
        return _FakeUser(user_id)

    monkeypatch.setattr(document_share_store, "build_context_for_user_id", _ctx)


@pytest.mark.asyncio
async def test_create_and_list_roundtrip(store_env):
    user = _FakeUser("user-1")

    share = await document_share_store.create_share(
        user, vault_id="vault-abc", recipient="advocate@example.org", scope="view", message="here you go"
    )
    assert share.share_token.startswith("user-1:")
    assert share.scope == "view"
    assert share.access_count == 0
    assert share.is_legacy_row is False

    shares = await document_share_store.list_shares(user, vault_id="vault-abc")
    assert len(shares) == 1
    assert shares[0].share_token == share.share_token

    # Filtered to a different document — empty
    assert await document_share_store.list_shares(user, vault_id="other") == []


@pytest.mark.asyncio
async def test_shares_are_isolated_per_user(store_env):
    user_a = _FakeUser("user-a")
    user_b = _FakeUser("user-b")

    await document_share_store.create_share(user_a, "v1", "r1@x.org", "view")
    await document_share_store.create_share(user_b, "v2", "r2@x.org", "download")

    assert len(await document_share_store.list_shares(user_a)) == 1
    assert len(await document_share_store.list_shares(user_b)) == 1


@pytest.mark.asyncio
async def test_resolve_share_by_owner_scoped_token(store_env, monkeypatch):
    _patch_ctx(monkeypatch)
    user = _FakeUser("user-3")

    share = await document_share_store.create_share(user, "vault-9", "r@x.org", "download")

    resolved = await document_share_store.resolve_share(share.share_token)
    assert resolved is not None
    assert resolved.owner_user_id == "user-3"
    assert resolved.vault_id == "vault-9"
    assert resolved.scope == "download"

    # Unknown token resolves to None; malformed tokens return None safely
    assert await document_share_store.resolve_share("user-3:bogus") is None
    assert await document_share_store.resolve_share("nocolonbutnotindb") is None


@pytest.mark.asyncio
async def test_record_share_access_increments(store_env, monkeypatch):
    _patch_ctx(monkeypatch)
    user = _FakeUser("user-4")

    share = await document_share_store.create_share(user, "vault-7", "r@x.org", "view")
    await document_share_store.record_share_access(share.share_token)
    await document_share_store.record_share_access(share.share_token)

    resolved = await document_share_store.resolve_share(share.share_token)
    assert resolved.access_count == 2
    assert resolved.accessed_at is not None


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def scalar_one_or_none(self):
        return self._row

    def scalars(self):
        return self

    def all(self):
        return [self._row] if self._row else []


class _FakeDB:
    def __init__(self, row):
        self._row = row
        self.commits = 0

    async def execute(self, _query):
        return _FakeResult(self._row)

    async def commit(self):
        self.commits += 1
        return self.commits

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def _legacy_row(**overrides):
    base = dict(
        id="share-legacy-1", owner_user_id="user-5", vault_id="vault-old",
        recipient_identifier="old@x.org", scope="view", message=None,
        share_token="barelegacytoken", expires_at=None, accessed_at=None,
        access_count=3, created_at=utc_now(),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_legacy_bare_token_resolves_and_converges(store_env, monkeypatch):
    """A pre-migration bare token resolves via the legacy row and imports the
    share into the owner's vault on first access."""
    import app.core.database as database_mod

    _patch_ctx(monkeypatch)
    row = _legacy_row()
    monkeypatch.setattr(database_mod, "get_db_session", lambda: _FakeDB(row))

    view = await document_share_store.resolve_share("barelegacytoken")
    assert view is not None
    assert view.is_legacy_row is True
    assert view.vault_id == "vault-old"
    assert view.access_count == 3

    # Converged: the share now exists in the owner's vault with a scoped token
    user = _FakeUser("user-5")
    shares = await document_share_store.list_shares(user)
    assert len(shares) == 1
    assert shares[0].share_token == "user-5:barelegacytoken"

    # Owner-scoped resolution works for the migrated share
    migrated = await document_share_store.resolve_share("user-5:barelegacytoken")
    assert migrated is not None
    assert migrated.vault_id == "vault-old"


@pytest.mark.asyncio
async def test_migrate_legacy_shares_idempotent(store_env, monkeypatch):
    import app.core.database as database_mod

    _patch_ctx(monkeypatch)
    user = _FakeUser("user-6")
    rows = [_legacy_row(id="s1", owner_user_id="user-6", share_token="tok1"),
            _legacy_row(id="s2", owner_user_id="user-6", share_token="tok2")]
    monkeypatch.setattr(database_mod, "get_db_session", lambda: _FakeDBMulti(rows))

    imported_first = await document_share_store.migrate_legacy_shares(user)
    imported_second = await document_share_store.migrate_legacy_shares(user)

    assert imported_first == 2
    assert imported_second == 0

    shares = await document_share_store.list_shares(user)
    assert {s.share_token for s in shares} == {"user-6:tok1", "user-6:tok2"}


class _FakeDBMulti:
    def __init__(self, rows):
        self._rows = rows
        self.commits = 0

    async def execute(self, _query):
        result = SimpleNamespace()
        result.scalars = lambda: SimpleNamespace(all=lambda: self._rows)
        return result

    async def commit(self):
        self.commits += 1
        return self.commits

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.mark.asyncio
async def test_migrate_legacy_shares_safe_without_db(store_env):
    user = _FakeUser("user-7")
    assert await document_share_store.migrate_legacy_shares(user) == 0
