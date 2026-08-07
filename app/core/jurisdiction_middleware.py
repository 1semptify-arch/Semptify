"""
Jurisdiction Middleware
=======================
On every authenticated request, silently resolve the user's jurisdiction
from their IP address (once per session) and store it in LocationService.

After this runs, all downstream modules can call:
    location_service.get_user_location(user_id)
and get the correct state, county, city automatically — no UI required.

Design:
- Runs ONLY for authenticated users (cookie present)
- No-op if location already set (in-memory cache in LocationService)
- Never blocks the request — fires as a background task
- Never raises — all failures are silent debug logs
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Paths that don't need jurisdiction (static assets, health checks, etc.)
_SKIP_PREFIXES = (
    "/static/",
    "/favicon",
    "/health",
    "/api/location/",  # Location module handles its own jurisdiction
    "/api/states/detect/",
)


class JurisdictionMiddleware(BaseHTTPMiddleware):
    """
    Auto-detects user jurisdiction from IP on first authenticated request.
    Stores result in LocationService singleton for all downstream modules.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip non-user paths
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        # Only run for authenticated users
        user_id = self._get_user_id(request)
        if user_id:
            client_ip = self._get_client_ip(request)
            # Fire-and-forget: never await — never blocks the request
            import asyncio

            asyncio.ensure_future(self._detect(user_id, client_ip))

        return await call_next(request)

    @staticmethod
    def _get_user_id(request: Request) -> str | None:
        try:
            from app.core.cookie_auth import extract_user_id

            return extract_user_id(request)
        except Exception:
            return None

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        # Respect Cloudflare / reverse proxy headers
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "127.0.0.1"

    @staticmethod
    async def _detect(user_id: str, client_ip: str) -> None:
        try:
            from app.services.location_service import auto_detect_jurisdiction

            await auto_detect_jurisdiction(user_id, client_ip)
        except Exception as e:
            logger.debug("JurisdictionMiddleware: detection failed: %s", e)
