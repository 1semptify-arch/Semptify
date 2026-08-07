"""
Module Overlay Manager — runtime module toggle and dev mode.

Provides:
- is_module_enabled(name) — check if module is toggled on
- is_module_in_dev_mode(name) — check if strict logging should apply
- set_module_enabled(name, bool) — toggle without restart
- set_dev_mode(name, bool) — enable/disable strict logging
- get_module_status(name) — full row data for dashboards
- list_modules() — all modules with their status

DB is source of truth. In-memory cache with TTL for performance.
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ModuleStatus(str, Enum):
    """Canonical module lifecycle states."""
    UNKNOWN = "unknown"
    ACTIVE = "active"
    BETA = "beta"
    DEPRECATED = "deprecated"
    BROKEN = "broken"


@dataclass
class ModuleInfo:
    """In-memory representation of a module registry row."""
    name: str
    display_name: str
    description: str
    status: str
    is_enabled: bool
    dev_mode: bool
    version: str | None
    route_prefix: str | None
    depends_on: list[str]
    notes: str


class ModuleOverlayManager:
    """
    Manages module overlay state — toggles and dev mode.

    Single source of truth: module_registry PostgreSQL table.
    In-memory cache with CACHE_TTL_SECONDS for performance.
    """

    CACHE_TTL_SECONDS: int = 60

    def __init__(self) -> None:
        self._cache: dict[str, ModuleInfo] = {}
        self._cache_loaded_at: float = 0.0

    def _is_cache_fresh(self) -> bool:
        return (time.monotonic() - self._cache_loaded_at) < self.CACHE_TTL_SECONDS

    async def _refresh_from_db(self) -> None:
        try:
            from sqlalchemy import text

            from app.core.database import get_session_factory
            async with get_session_factory()() as session:
                result = await session.execute(text(
                    "SELECT name, display_name, description, status, is_enabled, "
                    "dev_mode, version, route_prefix, depends_on, notes "
                    "FROM module_registry"
                ))
                rows = result.fetchall()
            self._cache = {}
            for r in rows:
                self._cache[r.name] = ModuleInfo(
                    name=r.name,
                    display_name=r.display_name or r.name,
                    description=r.description or "",
                    status=r.status,
                    is_enabled=r.is_enabled,
                    dev_mode=r.dev_mode,
                    version=r.version,
                    route_prefix=r.route_prefix,
                    depends_on=r.depends_on or [],
                    notes=r.notes or "",
                )
            self._cache_loaded_at = time.monotonic()
            logger.debug("Module registry refreshed: %d rows", len(rows))
        except Exception as e:
            logger.warning("Module registry DB read failed: %s", e)

    async def _ensure_fresh(self) -> None:
        if not self._is_cache_fresh():
            await self._refresh_from_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def is_module_enabled(self, name: str) -> bool:
        """Check if a module is enabled (runtime toggle)."""
        await self._ensure_fresh()
        info = self._cache.get(name)
        if not info:
            logger.warning("Module %s not in registry — treating as disabled", name)
            return False
        return info.is_enabled and info.status not in (ModuleStatus.BROKEN.value, ModuleStatus.DEPRECATED.value)

    async def is_module_in_dev_mode(self, name: str) -> bool:
        """Check if module has dev_mode strict logging enabled."""
        await self._ensure_fresh()
        info = self._cache.get(name)
        return info.dev_mode if info else False

    async def get_module_status(self, name: str) -> dict[str, Any] | None:
        """Get full module info for dashboards."""
        await self._ensure_fresh()
        info = self._cache.get(name)
        if not info:
            return None
        return {
            "name": info.name,
            "display_name": info.display_name,
            "status": info.status,
            "is_enabled": info.is_enabled,
            "dev_mode": info.dev_mode,
            "version": info.version,
            "route_prefix": info.route_prefix,
            "depends_on": info.depends_on,
            "notes": info.notes,
        }

    async def list_modules(self) -> list[dict[str, Any]]:
        """List all modules with their status."""
        await self._ensure_fresh()
        return [
            {
                "name": info.name,
                "display_name": info.display_name,
                "status": info.status,
                "is_enabled": info.is_enabled,
                "dev_mode": info.dev_mode,
                "version": info.version,
            }
            for info in self._cache.values()
        ]

    async def set_module_enabled(self, name: str, enabled: bool, updated_by: str = "system") -> bool:
        """Toggle module on/off. Returns True if module exists."""
        from sqlalchemy import text

        from app.core.database import get_session_factory
        async with get_session_factory()() as session:
            result = await session.execute(text(
                "UPDATE module_registry SET is_enabled = :enabled, updated_by = :by, updated_at = NOW() "
                "WHERE name = :name RETURNING id"
            ), {"name": name, "enabled": enabled, "by": updated_by})
            row = result.fetchone()
            if not row:
                logger.warning("set_module_enabled: %s not found", name)
                return False
            await session.commit()
        # Update cache immediately
        if name in self._cache:
            self._cache[name].is_enabled = enabled
        logger.info("Module %s enabled=%s by %s", name, enabled, updated_by)
        return True

    async def set_dev_mode(self, name: str, dev_mode: bool, updated_by: str = "system") -> bool:
        """Enable/disable dev mode strict logging."""
        from sqlalchemy import text

        from app.core.database import get_session_factory
        async with get_session_factory()() as session:
            result = await session.execute(text(
                "UPDATE module_registry SET dev_mode = :dev_mode, updated_by = :by, updated_at = NOW() "
                "WHERE name = :name RETURNING id"
            ), {"name": name, "dev_mode": dev_mode, "by": updated_by})
            row = result.fetchone()
            if not row:
                logger.warning("set_dev_mode: %s not found", name)
                return False
            await session.commit()
        if name in self._cache:
            self._cache[name].dev_mode = dev_mode
        logger.info("Module %s dev_mode=%s by %s", name, dev_mode, updated_by)
        return True

    async def set_status(self, name: str, status: str, updated_by: str = "system") -> bool:
        """Set module status (unknown/active/beta/deprecated/broken)."""
        from sqlalchemy import text

        from app.core.database import get_session_factory
        async with get_session_factory()() as session:
            result = await session.execute(text(
                "UPDATE module_registry SET status = :status, updated_by = :by, updated_at = NOW() "
                "WHERE name = :name RETURNING id"
            ), {"name": name, "status": status, "by": updated_by})
            row = result.fetchone()
            if not row:
                return False
            await session.commit()
        if name in self._cache:
            self._cache[name].status = status
        logger.info("Module %s status=%s by %s", name, status, updated_by)
        return True

    def invalidate_cache(self) -> None:
        """Force next read to re-query DB."""
        self._cache_loaded_at = 0.0


# Global instance
module_overlay = ModuleOverlayManager()
