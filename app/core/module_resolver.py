"""
Module Resolver — Phase 2.2

Given a user's role, jurisdiction, gates, and device, returns the set of
module_paths the user is allowed to use. This is the single source of truth
for module visibility.

Resolution order per module:
  1. lifecycle check (dev_only/preview → admin only)
  2. role check (requires_role)
  3. jurisdiction check (requires_jurisdiction)
  4. gate check (requires_gate)
  5. feature_flag check (Feature enum value)

Results are cached per-user in Redis (TTL 5 min) to avoid recomputing on
every request. Cache is invalidated on:
  - role switch
  - gate change
  - admin flag change
  - module lifecycle change

Usage:
    from app.core.module_resolver import resolve_modules_for_user

    allowed = await resolve_modules_for_user(
        user_id="GUTabc12345",
        role="tenant",
        jurisdiction="MN",
        gates={"storage_connected", "vault_initialized"},
    )
    # allowed = {"app.modules.vault.router", "app.modules.timeline.router", ...}
"""

import logging
from typing import Iterable

from app.core.product_manifest import MANIFEST, ModuleEntry, ProductTier

logger = logging.getLogger(__name__)

# Cache TTL — how long resolved module sets stay in Redis
_CACHE_TTL_SECONDS: int = 300  # 5 minutes


def _lifecycle_visible_to_role(lifecycle: str, role: str) -> bool:
    """Check if a lifecycle stage is visible to a given role."""
    if lifecycle in ("dev_only", "preview"):
        return role == "admin"
    if lifecycle == "experimental":
        # Admins always see experimental; other roles require feature_flag check
        # (handled by caller via feature_flag field)
        return True
    if lifecycle == "beta":
        # Admins always see beta; other roles require feature_flag check
        return True
    # stable, internal — visible per requires_role
    return True


def _role_allowed(entry: ModuleEntry, role: str) -> bool:
    """Check if role is allowed for this module."""
    if not entry.requires_role:
        return True  # empty = all roles
    return role in entry.requires_role


def _jurisdiction_allowed(entry: ModuleEntry, jurisdiction: str | None) -> bool:
    """Check if jurisdiction is allowed for this module."""
    if not entry.requires_jurisdiction:
        return True  # empty = all jurisdictions
    if jurisdiction is None:
        return False
    return jurisdiction in entry.requires_jurisdiction


def _gate_allowed(entry: ModuleEntry, gates: Iterable[str]) -> bool:
    """Check if required gate is set for this module."""
    if not entry.requires_gate:
        return True  # no gate required
    return entry.requires_gate in set(gates)


async def _feature_flag_allowed(entry: ModuleEntry) -> bool:
    """Check if feature flag (if any) is enabled for this module."""
    if not entry.feature_flag:
        return True  # no flag required
    try:
        from app.core.features import features, Feature
        # feature_flag stores the Feature enum value string
        feature = Feature(entry.feature_flag)
        return await features.is_enabled(feature)
    except ValueError:
        # Unknown feature flag — log and allow (fail open for visibility)
        logger.warning(
            "ModuleResolver: module %s has unknown feature_flag '%s' — allowing",
            entry.module_path, entry.feature_flag,
        )
        return True
    except Exception as e:
        # Feature flag system unavailable — fail closed for safety
        logger.error(
            "ModuleResolver: feature flag check failed for %s: %s — failing closed",
            entry.module_path, e,
        )
        return False


async def _check_entry(
    entry: ModuleEntry,
    role: str,
    jurisdiction: str | None,
    gates: Iterable[str],
) -> bool:
    """Run all checks for a single module entry."""
    # 1. Lifecycle check
    if not _lifecycle_visible_to_role(entry.lifecycle, role):
        return False

    # 2. Role check
    if not _role_allowed(entry, role):
        return False

    # 3. Jurisdiction check
    if not _jurisdiction_allowed(entry, jurisdiction):
        return False

    # 4. Gate check
    if not _gate_allowed(entry, gates):
        return False

    # 5. Feature flag check
    if not await _feature_flag_allowed(entry):
        return False

    return True


async def resolve_modules(
    role: str,
    jurisdiction: str | None,
    gates: Iterable[str],
    device: str | None = None,
) -> set[str]:
    """Return the set of module_paths the current user is allowed to use.

    This is the pure resolution function — no caching, no user lookup.
    Use resolve_modules_for_user() for the cached, user-aware version.
    """
    gates_set = set(gates)
    resolved: set[str] = set()
    for entry in MANIFEST.all():
        if await _check_entry(entry, role, jurisdiction, gates_set):
            resolved.add(entry.module_path)
    return resolved


def _cache_key(user_id: str) -> str:
    """Build Redis cache key for a user's resolved module set."""
    return f"module_resolver:{user_id}"


async def resolve_modules_for_user(
    user_id: str,
    role: str,
    jurisdiction: str | None,
    gates: Iterable[str],
    device: str | None = None,
) -> set[str]:
    """Resolve modules for a specific user with Redis caching.

    Cache TTL is 5 minutes. Cache is invalidated on:
      - role switch
      - gate change
      - admin flag change
      - module lifecycle change

    Falls back to uncached resolution if Redis is unavailable.
    """
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis is not None:
            cache_key = _cache_key(user_id)
            cached = await redis.get(cache_key)
            if cached:
                return set(cached.split(","))
            # Cache miss — resolve and store
            resolved = await resolve_modules(role, jurisdiction, gates, device)
            if resolved:
                await redis.set(
                    cache_key,
                    ",".join(sorted(resolved)),
                    ex=_CACHE_TTL_SECONDS,
                )
            return resolved
    except Exception as e:
        logger.warning(
            "ModuleResolver: Redis unavailable, falling back to uncached resolution: %s",
            e,
        )

    # Fallback — no cache
    return await resolve_modules(role, jurisdiction, gates, device)


async def invalidate_user_cache(user_id: str) -> None:
    """Invalidate cached module set for a user.

    Call this when:
      - user switches role
      - user's gates change (e.g. vault_initialized set)
      - admin changes a feature flag affecting this user
      - module lifecycle changes
    """
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis is not None:
            await redis.delete(_cache_key(user_id))
    except Exception as e:
        logger.warning(
            "ModuleResolver: failed to invalidate cache for %s: %s",
            user_id, e,
        )


async def invalidate_all_caches() -> None:
    """Invalidate all cached module sets (admin bulk operation).

    Call this when:
      - module lifecycle changes (admin promotes/demotes a module)
      - feature flag changes globally
      - system-wide configuration change
    """
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis is not None:
            # Scan and delete all module_resolver:* keys
            async for key in redis.scan_iter(match="module_resolver:*"):
                await redis.delete(key)
    except Exception as e:
        logger.warning(
            "ModuleResolver: failed to invalidate all caches: %s",
            e,
        )


async def is_module_allowed(
    module_path: str,
    role: str,
    jurisdiction: str | None,
    gates: Iterable[str],
) -> bool:
    """Check if a single module is allowed for the given context.

    This is a fast path for middleware — avoids resolving the full set.
    """
    entry = MANIFEST.find(module_path)
    if entry is None:
        return False
    return await _check_entry(entry, role, jurisdiction, gates)


async def get_user_module_summary(
    role: str,
    jurisdiction: str | None,
    gates: Iterable[str],
) -> dict:
    """Return a summary of what modules the user can see, grouped by tier.

    Useful for admin UI and debugging.
    """
    gates_set = set(gates)
    by_tier: dict[str, list[dict]] = {}
    for entry in MANIFEST.all():
        allowed = await _check_entry(entry, role, jurisdiction, gates_set)
        tier_key = entry.tier.value
        if tier_key not in by_tier:
            by_tier[tier_key] = []
        by_tier[tier_key].append({
            "module_path": entry.module_path,
            "lifecycle": entry.lifecycle,
            "origin": entry.origin,
            "allowed": allowed,
            "visibility_label": entry.visibility_label,
            "dev_notes": entry.dev_notes,
        })
    return {
        "role": role,
        "jurisdiction": jurisdiction,
        "gates": sorted(gates_set),
        "by_tier": by_tier,
        "total_modules": len(MANIFEST.all()),
    }
