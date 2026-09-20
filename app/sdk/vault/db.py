"""Per-tenant vault SQLite datastore.

The vault database is a single SQLite file stored in the tenant's own
connected storage at ``VAULT_DB_FILE`` (``Semptify5.0/.semptify/vault.db``).
SQLite owns live reads/writes for journal, calendar/timeline, and
composer/preview pilot domains; JSON overlays remain export/provenance
output, not the live store.

Remote providers can't open SQLite in place. The runtime pattern is:

    local path -> open_local()  (pragmas + pending migrations on every open)
              -> work
              -> checkpoint_and_close()  (WAL truncated into the main file)
              -> upload the single .db file back

WAL sidecar files (``-wal``/``-shm``) never leave the local temp dir.

Migrations are embedded, numbered SQL files in ``migrations/`` applied in
order on open and gated by ``vault_meta.schema_version`` — there is no
shared server to run them centrally.

Encryption at rest is an open decision — no SQLCipher assumed.

Dependency envelope matches client.py: stdlib + ``app.core.vault_paths`` +
the storage provider. No FastAPI, SQLAlchemy, middleware, or navigation.
"""

from __future__ import annotations

import logging
import re
import shutil
import sqlite3
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.vault_paths import SYSTEM_FOLDER, VAULT_DB_FILE

from app.sdk.vault.errors import VaultError

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
VAULT_DB_FILENAME = "vault.db"
VAULT_DB_MIME = "application/octet-stream"

_MIGRATION_RE = re.compile(r"^(\d+)_.*\.sql$")


class VaultDbError(VaultError):
    """Vault SQLite file could not be created, opened, or synced."""


def _migration_files() -> list[tuple[int, Path]]:
    """Numbered migration files, ascending. ``NNNN_name.sql`` -> N."""
    files: list[tuple[int, Path]] = []
    for path in MIGRATIONS_DIR.glob("*.sql"):
        match = _MIGRATION_RE.match(path.name)
        if match:
            files.append((int(match.group(1)), path))
    return sorted(files)


def schema_version(conn: sqlite3.Connection) -> int:
    """Current ``vault_meta.schema_version``; 0 if the table does not exist."""
    try:
        row = conn.execute(
            "SELECT value FROM vault_meta WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row[0]) if row else 0


def _apply_pending_migrations(conn: sqlite3.Connection) -> list[int]:
    """Apply every migration above the current schema_version, in order.

    Each migration runs inside an explicit transaction so a failure cannot
    leave half-applied DDL. Returns the list of version numbers applied.
    """
    current = schema_version(conn)
    applied: list[int] = []
    for number, path in _migration_files():
        if number <= current:
            continue
        script = path.read_text(encoding="utf-8")
        # executescript() implicit-commits before running, so the transaction
        # must live INSIDE the script text — a failed migration then rolls
        # back its DDL instead of half-applying. Migration files must never
        # contain their own BEGIN/COMMIT statements.
        # Escape hatch: a first-line `-- @fk_off` marker runs the migration
        # with foreign_keys OFF (table-rebuild migrations only — DROP on a
        # parent table otherwise cascades into child tables). The pragma is
        # toggled outside the transaction; inside one it is a no-op.
        fk_off = script.lstrip().startswith("-- @fk_off")
        version_stmt = (
            "INSERT OR REPLACE INTO vault_meta (key, value)"
            f" VALUES ('schema_version', '{number}');"
        )
        try:
            if fk_off:
                conn.execute("PRAGMA foreign_keys = OFF")
            conn.executescript(f"BEGIN;\n{script}\n{version_stmt}\nCOMMIT;")
        except sqlite3.Error as exc:
            if conn.in_transaction:
                conn.rollback()
            raise VaultDbError(f"vault.db migration {path.name} failed: {exc}") from exc
        finally:
            if fk_off:
                conn.execute("PRAGMA foreign_keys = ON")
        applied.append(number)
        current = number
    return applied


def open_local(path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) a vault DB file at a local path.

    Sets the locked pragmas on every open and applies any pending embedded
    migrations. Caller owns the connection — finish with
    ``checkpoint_and_close()`` before uploading the file anywhere.
    """
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    _apply_pending_migrations(conn)
    return conn


def checkpoint_and_close(conn: sqlite3.Connection) -> None:
    """Fold the WAL back into the main file and close.

    Required before upload — the remote copy must be a single self-contained
    ``.db`` file with no live ``-wal``/``-shm`` sidecars.
    """
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()


async def _upload(storage, local: Path) -> None:
    await storage.upload_file(
        file_content=local.read_bytes(),
        destination_path=SYSTEM_FOLDER,
        filename=VAULT_DB_FILENAME,
        mime_type=VAULT_DB_MIME,
    )


async def ensure_remote(storage) -> dict:
    """Create or verify+migrate the vault DB in the tenant's storage.

    Idempotent: an existing file is downloaded, opened (running any pending
    migrations), and re-uploaded only if its schema_version advanced. A
    missing file is created at the current schema version and uploaded. An
    existing file that fails to open raises ``VaultDbError`` — the remote
    copy is never overwritten or destroyed.

    Returns ``{"success": True, "state": ..., "schema_version": int,
    "path": VAULT_DB_FILE}`` where state is ``created`` | ``verified`` |
    ``migrated``.
    """
    workdir = Path(tempfile.mkdtemp(prefix="semptify_vaultdb_"))
    local = workdir / VAULT_DB_FILENAME
    try:
        if await storage.file_exists(VAULT_DB_FILE):
            original = await storage.download_file(VAULT_DB_FILE)
            local.write_bytes(original)
            try:
                probe = sqlite3.connect(str(local))
                before = schema_version(probe)
                probe.close()
                conn = open_local(local)
            except sqlite3.Error as exc:
                raise VaultDbError(
                    f"Existing vault.db failed to open: {exc}"
                ) from exc
            after = schema_version(conn)
            checkpoint_and_close(conn)
            if after > before:
                # Provider API has no atomic rename: remove the stale copy,
                # upload the migrated one, and restore the original on
                # failure so a retry can never lose tenant data.
                await storage.delete_file(VAULT_DB_FILE)
                try:
                    await _upload(storage, local)
                except Exception:
                    try:
                        await storage.upload_file(
                            file_content=original,
                            destination_path=SYSTEM_FOLDER,
                            filename=VAULT_DB_FILENAME,
                            mime_type=VAULT_DB_MIME,
                        )
                    except Exception:
                        logger.critical(
                            "vault.db migration upload failed AND restore "
                            "failed — local copy retained in %s", workdir
                        )
                    raise
                state = "migrated"
            else:
                state = "verified"
            return {
                "success": True,
                "state": state,
                "schema_version": after,
                "path": VAULT_DB_FILE,
            }

        conn = open_local(local)
        version = schema_version(conn)
        checkpoint_and_close(conn)
        await storage.create_folder(SYSTEM_FOLDER)  # idempotent
        await _upload(storage, local)
        return {
            "success": True,
            "state": "created",
            "schema_version": version,
            "path": VAULT_DB_FILE,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def mutate_remote(storage, work: Callable[[sqlite3.Connection], Any]) -> Any:
    """Download vault.db, run ``work(conn)``, checkpoint, re-upload.

    The single write path for live vault data: pull the file, open it
    (pending migrations apply on open), mutate inside one commit, fold the
    WAL, and upload the self-contained file back. If ``work`` raises, the
    remote file is left untouched. If the re-upload fails, the original
    remote bytes are restored so a retry never loses committed state.

    Requires the file to already exist — provisioning (ensure_remote)
    creates it. Per-call cost is one download + one upload, so callers
    should batch mutations rather than call this per row.
    """
    workdir = Path(tempfile.mkdtemp(prefix="semptify_vaultdb_"))
    local = workdir / VAULT_DB_FILENAME
    try:
        if not await storage.file_exists(VAULT_DB_FILE):
            raise VaultDbError(
                f"vault.db not found at {VAULT_DB_FILE} — provisioning has not run"
            )
        original = await storage.download_file(VAULT_DB_FILE)
        local.write_bytes(original)
        try:
            conn = open_local(local)
        except sqlite3.Error as exc:
            raise VaultDbError(f"vault.db failed to open: {exc}") from exc
        try:
            result = work(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            checkpoint_and_close(conn)
        await storage.delete_file(VAULT_DB_FILE)
        try:
            await _upload(storage, local)
        except Exception:
            try:
                await storage.upload_file(
                    file_content=original,
                    destination_path=SYSTEM_FOLDER,
                    filename=VAULT_DB_FILENAME,
                    mime_type=VAULT_DB_MIME,
                )
            except Exception:
                logger.critical(
                    "vault.db write upload failed AND restore failed — "
                    "local copy retained in %s",
                    workdir,
                )
            raise
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
