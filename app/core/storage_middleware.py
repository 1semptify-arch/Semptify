"""
Semptify 5.0 - Storage Requirement Middleware

SECURITY POLICY:
Every user MUST have their own cloud storage connected.
System users and demo users are NEVER allowed to access the application.

This middleware enforces storage connection for all protected pages.
"""

import logging
from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Set

from app.core.user_id import parse_user_id, COOKIE_USER_ID
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect

logger = logging.getLogger("semptify.security")

# Redirect loop tracking cookie name
REDIRECT_LOOP_COOKIE = "semptify_redirect_loop_count"
MAX_REDIRECT_LOOPS = 3


# Pages that don't require storage (public/auth pages)
PUBLIC_PATHS: Set[str] = {
    # Root and static assets
    "/",
    "/favicon.ico",
    
    # Health & monitoring
    "/health",
    "/metrics",
    "/api/version",
    "/risc/google/webhook",  # Google Cross-Account Protection — no cookie
    
    # Preamble — single entry point, must always be reachable (no storage required)
    "/preamble",

    # Onboarding & special pages — all sub-routes must be public
    # (user has no cookie yet during onboarding)
    "/onboarding",
    "/onboarding/",
    "/onboarding/start",        # Smart entry point — new users have no cookie yet
    "/onboarding/max-redirects",
    "/onboarding/max-redirects/",
    "/onboarding/select-role.html",
    "/onboarding/role-select",
    "/onboarding/providers",
    "/onboarding/connect",
    "/onboarding/upload",
    "/onboarding/activate",
    "/onboarding/verify-vault",
    "/onboarding/status",
    "/onboarding/ssot-navigation",  # SSOT API for static file navigation
    
    # Storage/Auth flow (must be public to connect)
    "/storage",
    "/storage/",
    "/storage/providers",
    "/storage/auth",
    "/storage/callback",
    "/storage/logout",
    "/storage/logout-reset",
    "/storage/rehome",
    
    # Public policy pages (privacy, terms, disclaimer, contact, feedback)
    "/public",
    "/public/",

    # Welcome/setup pages
    "/welcome.html",
    "/storage_setup.html",
    "/setup_wizard.html",
    "/index.html",
    "/index-simple.html",
    "/activate-vault",
    
    # API docs (development only)
    "/docs",
    "/redoc",
    "/openapi.json",
    
    # GUI Navigation Hub
    "/gui",

    # Auto Mode Features
    "/auto-mode",
    "/auto-analysis",

    # Core navigation pages (public landing pages)
    "/home",
    "/library",
    "/office",
    "/tools",
    "/help",

    # Static assets
    "/static",
    "/css",
    "/js",
    "/build",
}

# Path prefixes that are always public
PUBLIC_PREFIXES = (
    "/storage/",
    "/static/",   # All static files are public (HTML, CSS, JS)
    "/public/",   # Policy pages: privacy, terms, disclaimer, contact, feedback
    "/onboarding/",  # All onboarding sub-routes public — new users have no cookie yet
    "/onboarding-assets/",  # Onboarding static files
    "/api/vault-installer/",  # Vault installer — auth checked by route
    "/debug/",  # TEMPORARY: diagnostic endpoints
)


def is_public_path(path: str) -> bool:
    """Check if path is public (doesn't require storage)."""
    # Exact match
    if path in PUBLIC_PATHS:
        return True
    
    # Prefix match
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    
    # Static assets (by extension)
    if path.endswith(('.css', '.js', '.png', '.jpg', '.ico', '.svg', '.woff', '.woff2')):
        return True

    # Root-level static HTML pages — auth is enforced client-side via JS.
    # These pages redirect to onboarding themselves when no valid cookie exists.
    if path.endswith('.html'):
        return True

    return False


def is_valid_storage_user(user_id: str) -> bool:
    """
    Validate user ID represents a real user with storage connected.

    SECURITY: First verifies the HMAC signature to reject tampered cookies.
    Then validates the raw user_id format (provider + role + unique).

    Valid format (before signing): <provider><role><8-char-random>
    Example: GU7x9kM2pQ = Google + User + 7x9kM2pQ
    """
    if not user_id:
        return False

    # Verify HMAC signature — strips it and returns raw user_id, or None if tampered
    from app.core.cookie_auth import verify_user_id
    raw = verify_user_id(user_id)
    if raw is None:
        return False
    user_id = raw

    # Block known system/demo patterns
    invalid_patterns = [
        "open-mode",
        "system",
        "test",
        "demo",
        "guest",
        "admin-",
        "su_",
        "SU_",
    ]
    
    user_lower = user_id.lower()
    for pattern in invalid_patterns:
        if pattern.lower() in user_lower:
            return False
    
    # Must be at least 10 chars
    if len(user_id) < 10:
        return False
    
    # Validate structure using parser
    provider, role, unique = parse_user_id(user_id)
    
    # Must have valid provider and role
    if not provider or not role or not unique:
        return False
    
    # Unique part must be at least 6 chars
    if len(unique) < 6:
        return False
    
    return True


class StorageRequirementMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces storage connection requirement.
    
    SECURITY POLICY:
    - All protected pages require a valid user with storage
    - System/demo users are blocked
    - Unauthenticated users are redirected to storage providers
    
    This ensures nobody can use the app without their own cloud storage.
    """
    
    def __init__(self, app, enforce: bool = True):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI application
            enforce: If False, only logs warnings (for debugging)
        """
        super().__init__(app)
        self.enforce = enforce
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Public paths don't need storage
        if is_public_path(path):
            return await call_next(request)
        
        # Get user ID from cookie — pass the signed cookie directly.
        # is_valid_storage_user() calls verify_user_id() internally.
        _raw_cookie = request.cookies.get(COOKIE_USER_ID)
        user_id = _raw_cookie

        # Check if valid storage user format
        if not is_valid_storage_user(user_id):
            # Log the issue
            if user_id:
                logger.warning(
                    "🚫 Invalid/system user blocked: user_id=%s path=%s",
                    user_id[:4] + "***" if user_id else "None",
                    path
                )
            else:
                logger.debug("No user cookie, redirecting to storage: path=%s", path)
            
            if not self.enforce:
                # Debug mode - just log and continue
                return await call_next(request)
            
            # For API calls, return JSON error
            if path.startswith("/api/"):
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "storage_required",
                        "message": "Please connect your cloud storage to continue",
                        "action": "redirect",
                        "redirect_url": navigation.get_onboarding_start()
                    }
                )
            
            # For HTML pages, route through onboarding (role selection first) - SSOT
            return RedirectResponse(
                url=navigation.get_onboarding_start(),
                status_code=302
            )
        
        # Extract raw user_id for database operations
        from app.core.cookie_auth import verify_user_id
        raw_user_id = verify_user_id(user_id)
        if not raw_user_id:
            raw_user_id = user_id  # fallback
        
        # ── Silent Token Refresh ─────────────────────────────────────────────
        # Try to silently refresh expired tokens before proceeding.
        # If refresh fails, user will be redirected to reconnect flow.
        from app.core.auto_refresh import get_valid_token_or_redirect
        from app.core.database import get_session_factory
        
        factory = get_session_factory()
        async with factory() as refresh_db:
            token, reconnect_url = await get_valid_token_or_redirect(
                raw_user_id,
                return_to=path,
                db=refresh_db
            )
            
            if reconnect_url:
                # Silent refresh failed - need full reauth
                if path.startswith("/api/"):
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "token_expired",
                            "message": "Your storage connection expired. Please reconnect.",
                            "action": "redirect",
                            "redirect_url": reconnect_url
                        }
                    )
                
                return RedirectResponse(url=reconnect_url, status_code=302)
            
            # Token refreshed successfully or already valid - continue
            logger.debug(f"Silent refresh succeeded or token valid for user {raw_user_id[:6]}***")
        
        # Valid user — check onboarding gate state via the canonical single reader.
        # All gate decisions flow through get_onboarding_state(); nothing else reads
        # User.completed_groups directly for enforcement in this middleware.
        if self.enforce:
            try:
                import logging as _logging
                from app.core.database import get_session_factory
                from app.core.onboarding_state import get_onboarding_state

                _factory = get_session_factory()
                async with _factory() as _db:
                    ob_state = await get_onboarding_state(raw_user_id, _db)

                # ── Stale cookie: valid format but no DB row ──────────────────
                # get_onboarding_state returns all-False when user not found.
                # Distinguish "not found" from "found but incomplete" by checking
                # whether the storage gate was set — if everything is False AND
                # the user ID looks valid, treat as stale.
                if not ob_state.storage_connected and not ob_state.vault_initialized:
                    # Re-query just to detect "no row" vs "row exists, gates empty"
                    from sqlalchemy import select as _select
                    from app.models.models import User as _User
                    _stale_factory = get_session_factory()
                    async with _stale_factory() as _check_db:
                        _exists = await _check_db.execute(
                            _select(_User.id).where(_User.id == raw_user_id)
                        )
                        _row = _exists.scalar_one_or_none()

                    if _row is None:
                        logger.warning(
                            "User ID %s valid format but no DB record — clearing stale cookie",
                            raw_user_id[:4] + "***",
                        )
                        if path.startswith("/api/"):
                            return JSONResponse(
                                status_code=401,
                                content={
                                    "error": "storage_required",
                                    "message": "Session expired. Please reconnect your storage.",
                                    "action": "redirect",
                                    "redirect_url": "/storage/logout-reset",
                                },
                            )
                        logout_reset_stage = navigation.get_stage("logout_reset")
                        logout_reset_path = logout_reset_stage.path if logout_reset_stage else "/storage/logout-reset"
                        return ssot_redirect(logout_reset_path, context="storage_middleware session expired")

                # ── Onboarding incomplete ─────────────────────────────────────
                if not ob_state.is_fully_onboarded:
                    loop_count_str = request.cookies.get(REDIRECT_LOOP_COOKIE, "0")
                    try:
                        loop_count = int(loop_count_str)
                    except ValueError:
                        loop_count = 0

                    if loop_count >= MAX_REDIRECT_LOOPS:
                        if path.startswith("/api/"):
                            return JSONResponse(
                                status_code=401,
                                content={
                                    "error": "redirect_loop_max",
                                    "message": "Too many redirect attempts. Please review setup instructions.",
                                    "action": "redirect",
                                    "redirect_url": "/onboarding/max-redirects",
                                },
                            )
                        max_redirects_stage = navigation.get_stage("max_redirects")
                        max_redirects_path = max_redirects_stage.path if max_redirects_stage else "/onboarding/max-redirects"
                        response = ssot_redirect(max_redirects_path, context="storage_middleware redirect loop max")
                        response.delete_cookie(REDIRECT_LOOP_COOKIE)
                        return response

                    loop_count += 1

                    if path.startswith("/api/"):
                        return JSONResponse(
                            status_code=401,
                            content={
                                "error": "onboarding_incomplete",
                                "message": "Please complete onboarding to continue",
                                "action": "redirect",
                                "redirect_url": ob_state.next_required_path or "/onboarding/",
                            },
                        )

                    # Send user to the exact next required step (not just /onboarding/start)
                    next_path = ob_state.next_required_path
                    if next_path is None:
                        onboarding_start_stage = navigation.get_stage("onboarding_start")
                        next_path = onboarding_start_stage.path if onboarding_start_stage else "/onboarding/start"

                    response = ssot_redirect(next_path, context="storage_middleware incomplete onboarding")
                    response.set_cookie(
                        key=REDIRECT_LOOP_COOKIE,
                        value=str(loop_count),
                        max_age=3600,
                        httponly=True,
                        samesite="lax",
                    )
                    return response

            except Exception:
                # DB unavailable — degrade gracefully, format validation passed above.
                pass

        return await call_next(request)
