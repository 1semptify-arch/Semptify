"""
Capability System — Per-user Feature Module Access Control
==========================================================

Public API:
    seed_capability_defaults(user_id, role, session)  — call on first login
    get_user_capabilities(user_id, session)            — returns set of active module_names
    can_load_module(user_id, module_name, session)     — True if user has access
    grant_capability(user_id, module_name, granted_by, session)
    revoke_capability(user_id, module_name, session)

Architecture:
    - Pipeline modules are NEVER stored here. They are always-on.
    - Only Feature Modules (user-loadable) get rows in user_capabilities.
    - Defaults are seeded from CAPABILITY_DEFAULTS in product_manifest.py.
    - Admin role gets all modules via the "__all__" sentinel.
    - Redis caches the capability set per user for the session duration.
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utc import utc_now

logger = logging.getLogger(__name__)

_CACHE_TTL = 3600  # 1 hour — capability sets are stable within a session


# =============================================================================
# Internal helpers
# =============================================================================

def _cache_key(user_id: str) -> str:
    return f"capabilities:{user_id}"


async def _cache_get(user_id: str) -> Optional[set[str]]:
    """Read capability set from Redis. Returns None on miss or Redis unavailable."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            return None
        raw = await redis.smembers(_cache_key(user_id))
        if raw:
            return {v.decode() if isinstance(v, bytes) else v for v in raw}
        return None
    except Exception as exc:
        logger.debug("Capability cache read skipped: %s", exc)
        return None


async def _cache_set(user_id: str, modules: set[str]) -> None:
    """Write capability set to Redis with TTL."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            return
        key = _cache_key(user_id)
        if modules:
            await redis.sadd(key, *modules)
            await redis.expire(key, _CACHE_TTL)
    except Exception as exc:
        logger.debug("Capability cache write skipped: %s", exc)


async def _cache_invalidate(user_id: str) -> None:
    """Remove cached capability set for a user."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            return
        await redis.delete(_cache_key(user_id))
    except Exception as exc:
        logger.debug("Capability cache invalidation skipped: %s", exc)


# =============================================================================
# Public API
# =============================================================================

async def seed_capability_defaults(
    user_id: str,
    role: str,
    session: AsyncSession,
) -> int:
    """
    Seed user_capabilities with role defaults on first login.

    Only inserts rows that don't already exist — safe to call on every login.
    Returns the number of new rows inserted.
    """
    from app.models.models import UserCapability
    from app.core.product_manifest import CAPABILITY_DEFAULTS, MANIFEST

    defaults = CAPABILITY_DEFAULTS.get(role, CAPABILITY_DEFAULTS.get("tenant", []))

    if defaults == ["__all__"]:
        defaults = [e.module_path for e in MANIFEST.all()]

    existing_result = await session.execute(
        select(UserCapability.module_name).where(
            UserCapability.user_id == user_id,
            UserCapability.is_active == True,
        )
    )
    existing = {row[0] for row in existing_result.fetchall()}

    inserted = 0
    for module_name in defaults:
        if module_name not in existing:
            session.add(UserCapability(
                user_id=user_id,
                module_name=module_name,
                is_active=True,
                source="role_default",
                granted_at=utc_now(),
                updated_at=utc_now(),
            ))
            inserted += 1

    if inserted:
        await session.commit()
        await _cache_invalidate(user_id)
        logger.info("Seeded %d capability defaults for user %s (role=%s)", inserted, user_id, role)

    return inserted


async def get_user_capabilities(
    user_id: str,
    session: AsyncSession,
) -> set[str]:
    """
    Return the set of active module_names for a user.
    Reads from Redis cache first; falls back to DB.
    """
    cached = await _cache_get(user_id)
    if cached is not None:
        return cached

    from app.models.models import UserCapability

    result = await session.execute(
        select(UserCapability.module_name).where(
            UserCapability.user_id == user_id,
            UserCapability.is_active == True,
        )
    )
    modules = {row[0] for row in result.fetchall()}

    await _cache_set(user_id, modules)
    return modules


async def can_load_module(
    user_id: str,
    module_name: str,
    session: AsyncSession,
) -> bool:
    """
    Return True if the user has the given module active.
    Fast path: Redis cache hit. Slow path: DB query + cache fill.
    """
    capabilities = await get_user_capabilities(user_id, session)
    return module_name in capabilities


async def grant_capability(
    user_id: str,
    module_name: str,
    session: AsyncSession,
    granted_by: Optional[str] = None,
    source: str = "admin_grant",
) -> None:
    """
    Grant a capability to a user. Upserts the row (inserts or re-activates).
    Invalidates the Redis cache.
    """
    from app.models.models import UserCapability

    result = await session.execute(
        select(UserCapability).where(
            UserCapability.user_id == user_id,
            UserCapability.module_name == module_name,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.is_active = True
        existing.source = source
        existing.granted_by = granted_by
        existing.updated_at = utc_now()
    else:
        session.add(UserCapability(
            user_id=user_id,
            module_name=module_name,
            is_active=True,
            source=source,
            granted_by=granted_by,
            granted_at=utc_now(),
            updated_at=utc_now(),
        ))

    await session.commit()
    await _cache_invalidate(user_id)
    logger.info("Capability granted: user=%s module=%s source=%s by=%s",
                user_id, module_name, source, granted_by)


async def revoke_capability(
    user_id: str,
    module_name: str,
    session: AsyncSession,
    revoked_by: Optional[str] = None,
) -> None:
    """
    Revoke a capability from a user. Sets is_active=False (keeps audit trail).
    Invalidates the Redis cache.
    """
    from app.models.models import UserCapability

    result = await session.execute(
        select(UserCapability).where(
            UserCapability.user_id == user_id,
            UserCapability.module_name == module_name,
        )
    )
    cap = result.scalar_one_or_none()

    if cap:
        cap.is_active = False
        cap.updated_at = utc_now()
        await session.commit()
        await _cache_invalidate(user_id)
        logger.info("Capability revoked: user=%s module=%s by=%s",
                    user_id, module_name, revoked_by)
