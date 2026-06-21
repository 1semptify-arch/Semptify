"""
Module Runtime Overrides — Phase 2.4

Admin-managed runtime overrides for module lifecycle and feature flags.
This is the persistence layer for the ModuleFlagOverlay admin UI.

Overrides are stored in the `module_overrides` PostgreSQL table and cached
in-process for fast lookup by module_resolver.py.

Override fields:
  - lifecycle: Override the declared lifecycle (e.g. promote 'beta' -> 'stable')
  - feature_flag: Override the feature flag gating (e.g. force-enable a flag)
  - disabled: If True, module is hidden from all users regardless of other checks
  - notes: Admin notes about why this override exists

When an override is set, module_resolver._check_entry() consults the override
instead of (or in addition to) the static ModuleEntry from MANIFEST.

SSOT: This module is the ONLY place that writes overrides. The admin UI
calls these functions. The resolver reads from get_override().
"""

import logging
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.product_manifest import MANIFEST, ModuleEntry
from app.core.utc import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# In-process cache (so resolver doesn't hit DB on every request)
# =============================================================================

class _OverrideCache:
    """In-process cache of module overrides.

    Keyed by module_path. Values are dicts with keys:
        lifecycle: str | None
        feature_flag: str | None
        disabled: bool
        notes: str
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self._loaded: bool = False

    def get(self, module_path: str) -> Optional[dict]:
        return self._store.get(module_path)

    def set(self, module_path: str, override: dict) -> None:
        self._store[module_path] = override

    def remove(self, module_path: str) -> None:
        self._store.pop(module_path, None)

    def clear(self) -> None:
        self._store.clear()
        self._loaded = False

    def all(self) -> dict[str, dict]:
        return dict(self._store)

    @property
    def loaded(self) -> bool:
        return self._loaded

    def mark_loaded(self) -> None:
        self._loaded = True


_CACHE = _OverrideCache()


# =============================================================================
# Public API
# =============================================================================

async def load_overrides(db: AsyncSession) -> None:
    """Load all overrides from DB into the in-process cache.

    Call this once at startup or when the cache is stale.
    """
    try:
        result = await db.execute(
            text(
                "SELECT module_path, lifecycle, feature_flag, disabled, notes "
                "FROM module_overrides"
            )
        )
        rows = result.fetchall()
        _CACHE.clear()
        for row in rows:
            _CACHE.set(row.module_path, {
                "lifecycle": row.lifecycle,
                "feature_flag": row.feature_flag,
                "disabled": bool(row.disabled),
                "notes": row.notes or "",
            })
        _CACHE.mark_loaded()
        logger.info("ModuleOverrides: loaded %d overrides from DB", len(rows))
    except Exception as e:
        # Table may not exist yet — fail open with empty overrides
        logger.warning("ModuleOverrides: failed to load from DB: %s — starting empty", e)
        _CACHE.clear()
        _CACHE.mark_loaded()


async def get_override(module_path: str, db: Optional[AsyncSession] = None) -> Optional[dict]:
    """Get the runtime override for a module, if any.

    Returns None if no override is set. Returns a dict with keys
    lifecycle, feature_flag, disabled, notes if an override exists.
    """
    if not _CACHE.loaded and db is not None:
        await load_overrides(db)
    return _CACHE.get(module_path)


def get_override_sync(module_path: str) -> Optional[dict]:
    """Synchronous version for use in resolver hot path.

    Returns None if cache not loaded or no override exists.
    """
    if not _CACHE.loaded:
        return None
    return _CACHE.get(module_path)


async def set_override(
    db: AsyncSession,
    module_path: str,
    lifecycle: Optional[str] = None,
    feature_flag: Optional[str] = None,
    disabled: Optional[bool] = None,
    notes: str = "",
) -> dict:
    """Set or update an override for a module.

    Creates the override if it doesn't exist, updates if it does.
    Returns the override dict.
    """
    # Validate module exists in manifest
    entry = MANIFEST.find(module_path)
    if entry is None:
        raise ValueError(f"Module '{module_path}' not found in manifest")

    # Validate lifecycle if provided
    if lifecycle is not None:
        allowed = ("stable", "beta", "experimental", "dev_only", "preview", "internal")
        if lifecycle not in allowed:
            raise ValueError(
                f"lifecycle '{lifecycle}' invalid. Must be one of {allowed}"
            )

    # Build override dict
    override = {
        "lifecycle": lifecycle,
        "feature_flag": feature_flag,
        "disabled": bool(disabled) if disabled is not None else False,
        "notes": notes,
    }

    # Upsert into DB
    try:
        await db.execute(
            text(
                "INSERT INTO module_overrides "
                "(module_path, lifecycle, feature_flag, disabled, notes, updated_at) "
                "VALUES (:mp, :lc, :ff, :dis, :notes, :ts) "
                "ON CONFLICT (module_path) DO UPDATE SET "
                "lifecycle = EXCLUDED.lifecycle, "
                "feature_flag = EXCLUDED.feature_flag, "
                "disabled = EXCLUDED.disabled, "
                "notes = EXCLUDED.notes, "
                "updated_at = EXCLUDED.updated_at"
            ),
            {
                "mp": module_path,
                "lc": lifecycle,
                "ff": feature_flag,
                "dis": bool(disabled) if disabled is not None else False,
                "notes": notes,
                "ts": utc_now(),
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("ModuleOverrides: failed to set override for %s: %s", module_path, e)
        raise RuntimeError(f"Failed to persist override: {e}") from e

    # Update in-process cache
    _CACHE.set(module_path, override)
    logger.info(
        "ModuleOverrides: set override for %s — lifecycle=%s ff=%s disabled=%s",
        module_path, lifecycle, feature_flag, override["disabled"],
    )
    return override


async def delete_override(db: AsyncSession, module_path: str) -> bool:
    """Remove an override, reverting to the static MANIFEST declaration.

    Returns True if an override was deleted, False if none existed.
    """
    try:
        result = await db.execute(
            text("DELETE FROM module_overrides WHERE module_path = :mp RETURNING module_path"),
            {"mp": module_path},
        )
        deleted = result.fetchone() is not None
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("ModuleOverrides: failed to delete override for %s: %s", module_path, e)
        raise RuntimeError(f"Failed to delete override: {e}") from e

    if deleted:
        _CACHE.remove(module_path)
        logger.info("ModuleOverrides: deleted override for %s", module_path)
    return deleted


async def list_overrides(db: AsyncSession) -> list[dict]:
    """List all active overrides with their module metadata.

    Returns a list of dicts with module_path, override fields, and the
    original MANIFEST declaration for comparison.
    """
    if not _CACHE.loaded:
        await load_overrides(db)

    overrides = []
    for module_path, override in _CACHE.all().items():
        entry = MANIFEST.find(module_path)
        overrides.append({
            "module_path": module_path,
            "override": override,
            "declared": {
                "lifecycle": entry.lifecycle if entry else None,
                "feature_flag": entry.feature_flag if entry else None,
                "tier": entry.tier.value if entry else None,
            },
        })
    return overrides


def effective_entry(entry: ModuleEntry) -> ModuleEntry:
    """Return a ModuleEntry with runtime overrides applied.

    This is the pure function the resolver uses. It does NOT consult the DB —
    it only reads from the in-process cache. If the cache is not loaded,
    returns the entry unchanged.

    For disabled modules, returns the entry with lifecycle='dev_only' so
    only admins can see it (and they'll see it's disabled in the UI).
    """
    override = get_override_sync(entry.module_path)
    if override is None:
        return entry

    # If disabled, force dev_only (admin only)
    if override.get("disabled"):
        return _with_fields(entry, lifecycle="dev_only")

    # Apply lifecycle override
    new_lifecycle = override.get("lifecycle") or entry.lifecycle
    new_feature_flag = override.get("feature_flag")
    if new_feature_flag is None:
        new_feature_flag = entry.feature_flag

    return _with_fields(entry, lifecycle=new_lifecycle, feature_flag=new_feature_flag)


def _with_fields(entry: ModuleEntry, **updates) -> ModuleEntry:
    """Create a new ModuleEntry with updated fields (since it's frozen)."""
    from dataclasses import replace
    return replace(entry, **updates)


# =============================================================================
# DB Schema Initialization
# =============================================================================

async def ensure_schema(db: AsyncSession) -> None:
    """Create the module_overrides table if it doesn't exist.

    Call this at app startup.
    """
    try:
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS module_overrides (
                    module_path TEXT PRIMARY KEY,
                    lifecycle TEXT,
                    feature_flag TEXT,
                    disabled BOOLEAN NOT NULL DEFAULT FALSE,
                    notes TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await db.commit()
        logger.info("ModuleOverrides: schema ensured (module_overrides table)")
    except Exception as e:
        await db.rollback()
        logger.warning("ModuleOverrides: schema init failed: %s", e)
