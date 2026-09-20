"""Vault SQLite datastore — schema v1, pragmas, embedded migrations, remote sync."""

import sqlite3
from unittest.mock import AsyncMock

import pytest

from app.core.vault_paths import SYSTEM_FOLDER, VAULT_DB_FILE
from app.sdk.vault import db as vault_db
from app.sdk.vault.db import VaultDbError

EXPECTED_TABLES = {
    "vault_meta",
    "documents",
    "document_fields",
    "overlays",
    "share_tokens",
    "contacts",
    "appointments",
    "interactions",
    "journal_entries",
    "timeline_events",
    "ledger_entries",
    "dispute_packets",
    "resource_directory",
}


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
        from app.services.storage.base import StorageFile
        from app.core.utc import utc_now

        return StorageFile(
            id="fake",
            name=filename,
            path=f"{destination_path}/{filename}",
            size=len(file_content),
            mime_type=mime_type or "application/octet-stream",
            modified_at=utc_now(),
            is_folder=False,
        )

    async def delete_file(self, path: str) -> bool:
        return self.files.pop(path, None) is not None

    async def create_folder(self, path: str) -> bool:
        self.files.setdefault(path, b"<folder>")
        return True


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def test_open_local_creates_schema_v1(tmp_path):
    conn = vault_db.open_local(tmp_path / "vault.db")
    assert EXPECTED_TABLES <= _table_names(conn)
    assert vault_db.schema_version(conn) == 2
    row = conn.execute(
        "SELECT value FROM vault_meta WHERE key='processed_document_count'"
    ).fetchone()
    assert row == ("0",)
    vault_db.checkpoint_and_close(conn)


def test_open_local_sets_pragmas(tmp_path):
    conn = vault_db.open_local(tmp_path / "vault.db")
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1
    vault_db.checkpoint_and_close(conn)


def test_open_local_is_idempotent(tmp_path):
    path = tmp_path / "vault.db"
    vault_db.checkpoint_and_close(vault_db.open_local(path))
    conn = vault_db.open_local(path)  # second open: no migrations re-run
    assert vault_db.schema_version(conn) == 2
    vault_db.checkpoint_and_close(conn)


def test_foreign_keys_enforced(tmp_path):
    conn = vault_db.open_local(tmp_path / "vault.db")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO document_fields (id, document_id, label, created_at, updated_at)"
            " VALUES ('f1', 'missing-doc', 'x', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
    conn.rollback()
    vault_db.checkpoint_and_close(conn)


def test_doc_type_check_constraint(tmp_path):
    conn = vault_db.open_local(tmp_path / "vault.db")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO documents (id, name, doc_type, uploaded_at, storage_ref,"
            " created_at, updated_at) VALUES ('d1','x','bogus','t','ref','t','t')"
        )
    conn.rollback()
    vault_db.checkpoint_and_close(conn)


def test_migration_runner_gates_on_schema_version(tmp_path, monkeypatch):
    migdir = tmp_path / "migrations"
    migdir.mkdir()
    (migdir / "0001_base.sql").write_text(
        "CREATE TABLE vault_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);\n"
        "CREATE TABLE first_t (id TEXT PRIMARY KEY);\n"
        "INSERT INTO vault_meta (key, value) VALUES ('schema_version', '1');",
        encoding="utf-8",
    )
    (migdir / "0002_later.sql").write_text(
        "CREATE TABLE second_t (id TEXT PRIMARY KEY);", encoding="utf-8"
    )
    monkeypatch.setattr(vault_db, "MIGRATIONS_DIR", migdir)

    path = tmp_path / "vault.db"
    conn = vault_db.open_local(path)
    assert vault_db.schema_version(conn) == 2
    assert {"vault_meta", "first_t", "second_t"} <= _table_names(conn)
    vault_db.checkpoint_and_close(conn)

    # Simulate a file already at v2: nothing re-applies on reopen.
    conn = vault_db.open_local(path)
    assert vault_db.schema_version(conn) == 2
    vault_db.checkpoint_and_close(conn)


def test_failed_migration_rolls_back(tmp_path, monkeypatch):
    migdir = tmp_path / "migrations"
    migdir.mkdir()
    (migdir / "0001_base.sql").write_text(
        "CREATE TABLE vault_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);\n"
        "INSERT INTO vault_meta (key, value) VALUES ('schema_version', '1');",
        encoding="utf-8",
    )
    (migdir / "0002_broken.sql").write_text("THIS IS NOT SQL;", encoding="utf-8")
    monkeypatch.setattr(vault_db, "MIGRATIONS_DIR", migdir)

    with pytest.raises(VaultDbError):
        vault_db.open_local(tmp_path / "vault.db")

    # version stays at 1 — the broken migration must not half-apply
    conn = sqlite3.connect(str(tmp_path / "vault.db"))
    assert vault_db.schema_version(conn) == 1
    conn.close()


@pytest.mark.anyio
async def test_ensure_remote_creates_and_uploads(tmp_path):
    storage = FakeStorageProvider()
    result = await vault_db.ensure_remote(storage)
    assert result["success"] is True
    assert result["state"] == "created"
    assert result["schema_version"] == 2
    assert VAULT_DB_FILE in storage.files
    assert storage.files[VAULT_DB_FILE].startswith(b"SQLite format 3")


@pytest.mark.anyio
async def test_ensure_remote_verifies_current_file(tmp_path):
    storage = FakeStorageProvider()
    await vault_db.ensure_remote(storage)
    uploads_after_create = storage.uploads

    result = await vault_db.ensure_remote(storage)
    assert result["state"] == "verified"
    assert result["schema_version"] == 2
    assert storage.uploads == uploads_after_create  # no needless re-upload


@pytest.mark.anyio
async def test_ensure_remote_migrates_stale_file(tmp_path, monkeypatch):
    storage = FakeStorageProvider()
    await vault_db.ensure_remote(storage)

    # Ship migration 0002 after the file already exists at v1.
    real_dir = vault_db.MIGRATIONS_DIR
    migdir = tmp_path / "migrations"
    migdir.mkdir()
    for f in real_dir.glob("*.sql"):
        (migdir / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    (migdir / "0003_extra.sql").write_text(
        "CREATE TABLE extra_t (id TEXT PRIMARY KEY);", encoding="utf-8"
    )
    monkeypatch.setattr(vault_db, "MIGRATIONS_DIR", migdir)

    result = await vault_db.ensure_remote(storage)
    assert result["state"] == "migrated"
    assert result["schema_version"] == 3
    assert VAULT_DB_FILE in storage.files

    # The re-uploaded file really is at v3.
    local = tmp_path / "roundtrip.db"
    local.write_bytes(storage.files[VAULT_DB_FILE])
    conn = vault_db.open_local(local)
    assert vault_db.schema_version(conn) == 3
    assert "extra_t" in _table_names(conn)
    vault_db.checkpoint_and_close(conn)


@pytest.mark.anyio
async def test_ensure_remote_refuses_corrupt_file():
    storage = FakeStorageProvider()
    storage.files[VAULT_DB_FILE] = b"not a sqlite database"
    with pytest.raises(VaultDbError):
        await vault_db.ensure_remote(storage)
    # The corrupt remote copy is left in place — never destroyed.
    assert storage.files[VAULT_DB_FILE] == b"not a sqlite database"
