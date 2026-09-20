"""Folder requirements — registry integrity + lazy-ensure behavior.

The testing routine for the folder-build system:
  1. registry integrity — every declared path is a real vault path under
     SEMPTIFY_ROOT, eager and lazy sets are disjoint, and every canonical
     folder is claimed by exactly one entry (no orphans, no double claims)
  2. provisioning contract — the eager set is exactly what the folders
     step creates (plus role folders), so a requirement edit can't
     silently change what gets provisioned
  3. lazy mechanism — ensure_vault_folders creates declared paths on a
     fake storage, tolerates existing folders, and fails loudly
  4. roadmap honesty — a folder may only be marked lazy when it declares
     an ensure hook (first write would fail without one)
"""

import pytest

from app.core import vault_paths as vp
from app.core.vault_folder_requirements import (
    FOLDER_REQUIREMENTS,
    eager_folders,
    folders_for,
    lazy_folders,
    lazy_without_hook,
)
from app.sdk.vault.folders import ensure_parent_for_file, ensure_vault_folders


class FakeStorage:
    """Dict-backed storage — create_folder tracks calls."""

    def __init__(self, existing=None, fail_on=None):
        self.folders = set(existing or [])
        self.fail_on = set(fail_on or [])
        self.calls = []

    async def create_folder(self, path):
        self.calls.append(path)
        if path in self.fail_on:
            return False
        self.folders.add(path)
        return True


def test_all_declared_paths_under_semptify_root():
    for name, entry in FOLDER_REQUIREMENTS.items():
        for path in entry["folders"]:
            assert path.startswith(vp.SEMPTIFY_ROOT + "/") or path == vp.SEMPTIFY_ROOT, (
                f"{name}: {path} escapes the vault root"
            )


def test_eager_and_lazy_are_disjoint():
    assert not set(eager_folders()) & set(lazy_folders())


def test_every_canonical_folder_is_claimed():
    claimed = set(eager_folders()) | set(lazy_folders())
    orphans = set(vp.CANONICAL_VAULT_FOLDERS) - claimed
    assert not orphans, f"canonical folders nobody claims: {orphans}"


def test_no_folder_claimed_twice():
    seen = {}
    for name, entry in FOLDER_REQUIREMENTS.items():
        for path in entry["folders"]:
            assert path not in seen, f"{path} claimed by both {seen[path]} and {name}"
            seen[path] = name


def test_lazy_requires_ensure_hook():
    for name, entry in FOLDER_REQUIREMENTS.items():
        if not entry.get("eager"):
            assert entry.get("ensure_hook"), (
                f"{name} is lazy but declares no ensure hook — first write would fail"
            )


def test_provisioning_spec_is_eager_set():
    from app.services.vault_provisioning import _provisioning_folder_spec

    spec = _provisioning_folder_spec("tenant")
    assert set(eager_folders()) <= set(spec.all_folders)
    # nothing lazy sneaks into provisioning
    assert not set(lazy_folders()) & set(spec.all_folders)


@pytest.mark.asyncio
async def test_ensure_creates_declared_folders():
    storage = FakeStorage()
    ok = await ensure_vault_folders(storage, [vp.VAULT_JOURNAL, vp.VAULT_LEDGER])
    assert ok
    assert storage.calls == [vp.VAULT_JOURNAL, vp.VAULT_LEDGER]


@pytest.mark.asyncio
async def test_ensure_tolerates_existing_folder():
    storage = FakeStorage(existing=[vp.VAULT_JOURNAL])
    ok = await ensure_vault_folders(storage, [vp.VAULT_JOURNAL])
    assert ok  # idempotent — one call, no pre-check


@pytest.mark.asyncio
async def test_ensure_fails_loudly():
    storage = FakeStorage(fail_on=[vp.VAULT_LEDGER])
    ok = await ensure_vault_folders(storage, [vp.VAULT_JOURNAL, vp.VAULT_LEDGER])
    assert not ok


@pytest.mark.asyncio
async def test_ensure_parent_for_file():
    storage = FakeStorage()
    ok = await ensure_parent_for_file(storage, vp.VAULT_JOURNAL_FILE)
    assert ok
    assert storage.calls == [vp.VAULT_JOURNAL]


def test_roadmap_entries_are_eager_with_null_hook():
    roadmap = lazy_without_hook()
    for name, folders in roadmap.items():
        entry = FOLDER_REQUIREMENTS[name]
        assert entry["eager"] is True
        assert entry["ensure_hook"] is None
        assert folders == entry["folders"]


def test_folders_for_known_and_unknown():
    assert vp.VAULT_JOURNAL in folders_for("journal")
    assert folders_for("nonexistent_feature") == []
