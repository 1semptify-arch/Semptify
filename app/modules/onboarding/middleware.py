"""
Onboarding Gate Middleware — enforces serial gates for onboarding.

Any request from a user who hasn't completed all gates gets redirected
to the appropriate onboarding step. This middleware is separate from
the storage_middleware in app/core/ — it only enforces ONBOARDING gates.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.cookie_auth import verify_user_id
from app.core.database import get_db_session
from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding.gates import get_first_incomplete_gate

logger = logging.getLogger(__name__)

# Paths that should NEVER be gated (public, static, health, etc.)
ALWAYS_ALLOW_PREFIXES = (
    "/static/",
    "/health",
    "/api/health",
    "/_debug",
    "/favicon.ico",
)


class OnboardingGateMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces onboarding gates.

    If a user has incomplete gates and is trying to access a protected route,
    they get redirected to the appropriate onboarding step.

    Routes within the onboarding prefix are ALWAYS allowed (otherwise
    the user could never complete onboarding).
    """

    def __init__(self, app, config: OnboardingConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Always allow onboarding routes themselves
        if path.startswith(self.config.route_prefix):
            return await call_next(request)

        # Always allow public/static paths
        for prefix in ALWAYS_ALLOW_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Check for user cookie
        _raw_cookie = request.cookies.get(self.config.cookie_name)
        cookie_value = str(_raw_cookie) if _raw_cookie is not None else None
        if not cookie_value:
            # No cookie = no user = not our problem (other middleware handles this)
            return await call_next(request)

        # Verify HMAC
        raw_uid = verify_user_id(cookie_value) if self.config.hmac_signed else cookie_value
        if not raw_uid:
            return await call_next(request)

        # Check gates
        try:
            async with get_db_session() as db:
                incomplete = await get_first_incomplete_gate(db, raw_uid, self.config.gates)
        except Exception as exc:
            logger.warning("Gate check failed for %s: %s", raw_uid[:6] + "***", exc)
            return await call_next(request)

        if incomplete is None:
            # All gates passed — allow
            return await call_next(request)

        # User has incomplete gates — redirect to onboarding status
        gate_routes = {
            "storage_connected": f"{self.config.route_prefix}/providers",
            "vault_initialized": f"{self.config.route_prefix}/vault-setup",
        }
        redirect_path = gate_routes.get(incomplete, f"{self.config.route_prefix}/status")

        logger.info(
            "Gate '%s' incomplete for user %s, redirecting to %s",
            incomplete,
            raw_uid[:6] + "***",
            redirect_path,
        )
        # Use SSOT-compliant redirect for internal navigation
        from app.core.ssot_guard import ssot_redirect

        return ssot_redirect(redirect_path, context="onboarding_gate_redirect")
