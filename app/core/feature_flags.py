"""Runtime feature flags.

Flags can be toggled without redeploying. The middleware checks a mapping of
path prefixes to flags and returns HTTP 503 when a flag is disabled, letting us
emergency-disable a route or integration without taking the whole site down.
"""

import logging
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("semptify.feature_flags")


class FeatureFlags:
    """Thread-safe in-memory feature flag store."""

    _flags: dict[str, bool] = {
        "admin_access": True,
        "copilot": True,
        "voice_to_text": True,
        "communication_import": True,
        "resource_directory": True,
    }

    @classmethod
    def is_enabled(cls, name: str) -> bool:
        """Return the current state of a flag, defaulting to True if unknown."""
        return cls._flags.get(name, True)

    @classmethod
    def set_flag(cls, name: str, enabled: bool) -> bool:
        """Set a flag and return its new state."""
        cls._flags[name] = enabled
        logger.info("Feature flag %s set to %s", name, enabled)
        return enabled

    @classmethod
    def toggle_flag(cls, name: str) -> bool:
        """Toggle a flag and return its new state."""
        new_state = not cls.is_enabled(name)
        return cls.set_flag(name, new_state)

    @classmethod
    def all_flags(cls) -> dict[str, bool]:
        """Return a copy of all flags."""
        return cls._flags.copy()


# Map URL path prefixes to flag names. Add new routes here as they are built.
ROUTE_FLAG_MAP = {
    "/admin": "admin_access",
    "/api/copilot": "copilot",
    "/tenant/copilot": "copilot",
    "/api/voice": "voice_to_text",
    "/api/import": "communication_import",
    "/api/resources": "resource_directory",
    "/tenant/resources": "resource_directory",
}


def flag_for_path(path: str) -> str | None:
    """Return the flag that guards a path, or None."""
    for prefix, flag_name in ROUTE_FLAG_MAP.items():
        if path.startswith(prefix):
            return flag_name
    return None


class FeatureFlagMiddleware(BaseHTTPMiddleware):
    """Return 503 Service Unavailable for routes whose feature flag is disabled."""

    async def dispatch(self, request: Request, call_next: Callable):
        flag_name = flag_for_path(request.url.path)
        if flag_name and not FeatureFlags.is_enabled(flag_name):
            logger.warning("Flag %s disabled; blocking %s", flag_name, request.url.path)
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service temporarily disabled",
                    "flag": flag_name,
                },
            )
        return await call_next(request)
