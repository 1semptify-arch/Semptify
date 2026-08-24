"""
Feature Flags System for Semptify.

Provides runtime feature toggling without code deployments.

Usage:
    from app.core.features import features, Feature

    if await features.is_enabled(Feature.AI_COPILOT):
        pass

    @require_feature(Feature.BETA_DASHBOARD)
    async def beta_dashboard():
        ...

    if await features.is_enabled_for_user(Feature.PREMIUM_EXPORT, user_id):
        pass
"""

import logging
from collections.abc import Callable
from enum import StrEnum
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from fastapi import HTTPException, status

from app.core.utc import utc_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Feature(StrEnum):
    """Feature flags enumeration."""

    AI_COPILOT = "ai_copilot"
    AI_DOCUMENT_ANALYSIS = "ai_document_analysis"
    AI_LEGAL_ADVICE = "ai_legal_advice"
    DOCUMENT_OCR = "document_ocr"
    DOCUMENT_SIGNING = "document_signing"
    BULK_UPLOAD = "bulk_upload"
    COURT_FORMS = "court_forms"
    COMPLAINT_WIZARD = "complaint_wizard"
    EVICTION_DEFENSE = "eviction_defense"
    PREMIUM_EXPORT = "premium_export"
    PREMIUM_TEMPLATES = "premium_templates"
    UNLIMITED_STORAGE = "unlimited_storage"
    BETA_DASHBOARD = "beta_dashboard"
    BETA_TIMELINE_V2 = "beta_timeline_v2"
    BETA_MESH_NETWORK = "beta_mesh_network"
    REDIS_CACHE = "redis_cache"
    DISTRIBUTED_MESH = "distributed_mesh"
    WEBSOCKET_EVENTS = "websocket_events"
    TWO_FACTOR_AUTH = "two_factor_auth"
    AUDIT_LOGGING = "audit_logging"
    RATE_LIMITING = "rate_limiting"
    EXPERIMENTAL_AI_MODEL = "experimental_ai_model"
    EXPERIMENTAL_UI = "experimental_ui"


# Code-level defaults — used when a flag has no DB row yet
DEFAULT_ENABLED: dict[str, bool] = {
    Feature.AI_COPILOT.value: True,
    Feature.AI_DOCUMENT_ANALYSIS.value: True,
    Feature.AI_LEGAL_ADVICE.value: True,
    Feature.DOCUMENT_OCR.value: True,
    Feature.DOCUMENT_SIGNING.value: False,
    Feature.BULK_UPLOAD.value: True,
    Feature.COURT_FORMS.value: True,
    Feature.COMPLAINT_WIZARD.value: True,
    Feature.EVICTION_DEFENSE.value: True,
    Feature.PREMIUM_EXPORT.value: False,
    Feature.PREMIUM_TEMPLATES.value: False,
    Feature.UNLIMITED_STORAGE.value: False,
    Feature.BETA_DASHBOARD.value: True,
    Feature.BETA_TIMELINE_V2.value: True,
    Feature.BETA_MESH_NETWORK.value: True,
    Feature.REDIS_CACHE.value: True,
    Feature.DISTRIBUTED_MESH.value: True,
    Feature.WEBSOCKET_EVENTS.value: True,
    Feature.TWO_FACTOR_AUTH.value: False,
    Feature.AUDIT_LOGGING.value: True,
    Feature.RATE_LIMITING.value: True,
    Feature.EXPERIMENTAL_AI_MODEL.value: False,
    Feature.EXPERIMENTAL_UI.value: False,
}


class FeatureFlagManager:
    """
    Feature flag manager — PostgreSQL is the single source of truth.

    Priority order (highest wins):
    1. Environment variables  FEATURE_<NAME>=true/false  (ops emergency override)
    2. PostgreSQL feature_flags table                    (admin-controlled, persistent)
    3. DEFAULT_ENABLED code defaults                     (fallback when row missing)

    In-memory cache with CACHE_TTL_SECONDS TTL avoids a DB hit on every request
    while staying live-updatable by admins without a redeploy.
    """

    CACHE_TTL_SECONDS: int = 60

    def __init__(self) -> None:
        self._cache: dict[str, bool] = {}
        self._cache_detail: dict[str, dict] = {}
        self._cache_loaded_at: float = 0.0
        self._env_overrides: dict[str, bool] = {}
        self._env_loaded: bool = False

    def _load_env_overrides(self) -> None:
        if self._env_loaded:
            return
        import os

        for feature in Feature:
            env_key = f"FEATURE_{feature.value.upper()}"
            val = os.environ.get(env_key)
            if val is not None:
                self._env_overrides[feature.value] = val.lower() in ("true", "1", "yes", "on")
                logger.debug("Feature %s overridden by env: %s", feature.value, self._env_overrides[feature.value])
        self._env_loaded = True

    def _is_cache_fresh(self) -> bool:
        import time

        return (time.monotonic() - self._cache_loaded_at) < self.CACHE_TTL_SECONDS

    def _apply_defaults_to_cache(self) -> None:
        for flag_name, enabled in DEFAULT_ENABLED.items():
            if flag_name not in self._cache:
                self._cache[flag_name] = enabled
                self._cache_detail[flag_name] = {
                    "flag_name": flag_name,
                    "enabled": enabled,
                    "rollout_percent": 100,
                    "allowed_roles": [],
                    "description": "",
                    "source": "default",
                }

    async def _refresh_from_db(self) -> None:
        import time

        try:
            from sqlalchemy import text

            from app.core.database import get_session_factory

            async with get_session_factory()() as session:
                result = await session.execute(
                    text("SELECT flag_name, enabled, rollout_percent, allowed_roles, description FROM feature_flags")
                )
                rows = result.fetchall()
            for row in rows:
                self._cache[row.flag_name] = row.enabled
                allowed_roles = row.allowed_roles
                if isinstance(allowed_roles, str):
                    # SQLite has no ARRAY type - allowed_roles is stored as
                    # JSON text there (nothing writes it yet, but be
                    # tolerant if something does in the future).
                    import json

                    try:
                        allowed_roles = json.loads(allowed_roles) if allowed_roles else []
                    except (ValueError, TypeError):
                        allowed_roles = []
                self._cache_detail[row.flag_name] = {
                    "flag_name": row.flag_name,
                    "enabled": row.enabled,
                    "rollout_percent": row.rollout_percent or 100,
                    "allowed_roles": allowed_roles or [],
                    "description": row.description or "",
                    "source": "database",
                }
            self._cache_loaded_at = time.monotonic()
            logger.debug("Feature flags refreshed from DB: %d rows", len(rows))
        except Exception as e:
            logger.warning("Feature flags DB read failed, falling back to cache/defaults: %s", e)
            if not self._cache:
                self._apply_defaults_to_cache()

    async def _ensure_fresh(self) -> None:
        self._load_env_overrides()
        if not self._is_cache_fresh():
            await self._refresh_from_db()
            self._apply_defaults_to_cache()

    def _resolve(self, flag_name: str) -> bool:
        if flag_name in self._env_overrides:
            return self._env_overrides[flag_name]
        return self._cache.get(flag_name, DEFAULT_ENABLED.get(flag_name, False))

    async def is_enabled(self, feature: Feature) -> bool:
        """Check if a feature is globally enabled."""
        await self._ensure_fresh()
        return self._resolve(feature.value)

    async def is_enabled_for_user(self, feature: Feature, user_id: str) -> bool:
        """Check if a feature is enabled for a specific user (rollout aware)."""
        await self._ensure_fresh()
        if feature.value in self._env_overrides:
            return self._env_overrides[feature.value]
        if not self._resolve(feature.value):
            return False
        rollout = self._cache_detail.get(feature.value, {}).get("rollout_percent", 100)
        if rollout < 100:
            user_hash = hash(f"{feature.value}:{user_id}") % 100
            if user_hash >= rollout:
                return False
        return True

    async def is_enabled_for_role(self, feature: Feature, role: str) -> bool:
        """Check if a feature is enabled for a specific role."""
        await self._ensure_fresh()
        if not self._resolve(feature.value):
            return False
        allowed_roles = self._cache_detail.get(feature.value, {}).get("allowed_roles") or []
        return not (allowed_roles and role not in allowed_roles)

    async def set_enabled(self, flag_name: str, enabled: bool, updated_by: str = "system") -> None:
        """Persist flag change to the DB and update in-memory cache immediately.

        Uses a Python-generated UTC timestamp passed as a bound parameter so the
        same code is safe against SQL injection and works on both PostgreSQL and
        SQLite (the ON CONFLICT ... DO UPDATE ... EXCLUDED syntax is supported
        by both).
        """
        from sqlalchemy import text

        from app.core.database import get_session_factory

        async with get_session_factory()() as session:
            updated_at = utc_now()
            await session.execute(
                text("""
                INSERT INTO feature_flags (flag_name, enabled, updated_by, updated_at)
                VALUES (:name, :enabled, :by, :updated_at)
                ON CONFLICT (flag_name) DO UPDATE
                    SET enabled    = EXCLUDED.enabled,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = EXCLUDED.updated_at
            """),
                {"name": flag_name, "enabled": enabled, "by": updated_by, "updated_at": updated_at},
            )
            await session.commit()
        self._cache[flag_name] = enabled
        logger.info("Feature flag %s set to %s by %s", flag_name, enabled, updated_by)

    async def get_all_flags(self) -> dict[str, Any]:
        """Return all flags with full detail for admin UI and diagnostics."""
        await self._ensure_fresh()
        result = {}
        for feature in Feature:
            detail = self._cache_detail.get(feature.value, {})
            result[feature.value] = {
                "enabled": self._resolve(feature.value),
                "rollout_percent": detail.get("rollout_percent", 100),
                "allowed_roles": detail.get("allowed_roles", []),
                "description": detail.get("description", ""),
                "source": detail.get("source", "default"),
                "env_override": feature.value in self._env_overrides,
            }
        return result

    async def get_status(self) -> dict[str, Any]:
        """Summary for health checks and admin dashboard."""
        await self._ensure_fresh()
        import time

        enabled_count = sum(1 for f in Feature if self._resolve(f.value))
        return {
            "total_features": len(Feature),
            "enabled_features": enabled_count,
            "disabled_features": len(Feature) - enabled_count,
            "env_overrides": len(self._env_overrides),
            "cache_age_seconds": round(time.monotonic() - self._cache_loaded_at, 1),
            "source": "postgresql",
        }

    def invalidate_cache(self) -> None:
        """Force next read to re-query DB. Call after admin flag changes."""
        self._cache_loaded_at = 0.0


# =============================================================================
# DB Schema Initialization
# =============================================================================
# alembic/versions/20260609_add_feature_flags_table.py creates this table for
# real deploys, but two things leave local dev without it:
#   1. Alembic auto-migration only runs when RENDER=true (see app/main.py) -
#      local dev never runs migrations at all, by design.
#   2. Even if it did, that migration uses sa.ARRAY for allowed_roles /
#      allowed_states, which SQLite does not support (same class of issue as
#      the pre-existing module_registry migration).
# ensure_schema() below mirrors the app/core/module_overrides.py pattern:
# a dialect-aware CREATE TABLE IF NOT EXISTS run at startup, so local SQLite
# dev gets a real table with the same default rows as the Postgres
# migration, without touching or replacing that migration.
_DEFAULT_FLAG_ROWS: list[tuple[str, bool, str]] = [
    ("eviction_defense_nd", True, "Enable eviction defense in North Dakota"),
    ("counterclaim_builder", False, "Enable counterclaim builder (legal only)"),
    ("advanced_analytics", False, "Enable advanced analytics dashboard"),
    ("new_ui_theme", False, "Enable new UI theme (gradual rollout)"),
    ("batch_operations", False, "Enable admin batch operations"),
]


def _dialect_name(db: "AsyncSession") -> str:
    dialect = getattr(db.bind, "dialect", None)
    return getattr(dialect, "name", "") if dialect else ""


async def ensure_schema(db: "AsyncSession") -> None:
    """Create the feature_flags table (and seed default rows) if missing.

    Safe to call on every startup - CREATE TABLE IF NOT EXISTS is a no-op on
    an already-migrated Postgres deploy; the seed insert only runs when the
    table is empty, so it never overwrites admin-set flags.
    """
    from sqlalchemy import text

    try:
        is_postgres = _dialect_name(db) == "postgresql"
        if is_postgres:
            id_col = "id SERIAL PRIMARY KEY"
            ts_type = "TIMESTAMPTZ"
            ts_default = "NOW()"
            roles_type = "TEXT[]"
        else:
            # SQLite (and most others): no SERIAL, no ARRAY, no NOW().
            id_col = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            ts_type = "TIMESTAMP"
            ts_default = "CURRENT_TIMESTAMP"
            roles_type = "TEXT"  # unused today (nothing writes allowed_roles yet)

        await db.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS feature_flags (
                    {id_col},
                    flag_name TEXT NOT NULL UNIQUE,
                    flag_type TEXT NOT NULL DEFAULT 'boolean',
                    enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    rollout_percent INTEGER NOT NULL DEFAULT 0,
                    allowed_roles {roles_type},
                    allowed_states {roles_type},
                    description TEXT,
                    created_by TEXT,
                    updated_by TEXT,
                    created_at {ts_type} NOT NULL DEFAULT {ts_default},
                    updated_at {ts_type} NOT NULL DEFAULT {ts_default}
                )
                """
            )
        )

        result = await db.execute(text("SELECT COUNT(*) FROM feature_flags"))
        existing_count = result.scalar() or 0
        if existing_count == 0:
            for flag_name, enabled, description in _DEFAULT_FLAG_ROWS:
                await db.execute(
                    text(
                        "INSERT INTO feature_flags (flag_name, flag_type, enabled, description, created_by) "
                        "VALUES (:name, 'boolean', :enabled, :desc, 'system')"
                    ),
                    {"name": flag_name, "enabled": enabled, "desc": description},
                )
            logger.info("FeatureFlags: seeded %d default rows", len(_DEFAULT_FLAG_ROWS))

        await db.commit()
        logger.info("FeatureFlags: schema ensured (feature_flags table)")
    except Exception as e:
        await db.rollback()
        logger.warning("FeatureFlags: schema init failed: %s", e)


# Global feature flag manager — single instance for the process
features = FeatureFlagManager()


def require_feature(feature: Feature):
    """Decorator to require a feature flag for an endpoint."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            if not await features.is_enabled(feature):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="This feature is not currently available",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_feature_for_user(feature: Feature, user_id_param: str = "user_id"):
    """Decorator to require a feature flag for a specific user."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            user_id = kwargs.get(user_id_param)
            if not user_id or not await features.is_enabled_for_user(feature, user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This feature is not available for your account",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
