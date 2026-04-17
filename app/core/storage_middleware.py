"""
Semptify 5.0 - Storage Requirement Middleware

SECURITY POLICY:
Every user MUST have their own cloud storage connected.
System users and demo users are NEVER allowed to access the application.

This middleware enforces storage connection for all protected pages.
"""

from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Set

from app.core.user_id import parse_user_id, COOKIE_USER_ID

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
    
    # Onboarding & special pages
    "/onboarding",
    "/onboarding/",
    "/onboarding/max-redirects",
    "/onboarding/max-redirects/",
    
    # Storage/Auth flow (must be public to connect)
    "/storage",
    "/storage/",
    "/storage/providers",
    "/storage/auth",
    "/storage/callback",
    "/storage/logout",
    "/storage/rehome",
    
    # Welcome/setup pages
    "/welcome.html",
    "/storage_setup.html",
    "/setup_wizard.html",
    "/index.html",
    "/index-simple.html",
    
    # API docs (development only)
    "/docs",
    "/redoc",
    "/openapi.json",
    
    # GUI Navigation Hub
    "/gui",
    
    # Auto Mode Features
    "/auto-mode",
    "/auto-analysis",
    
    # Static assets
    "/static",
    "/css",
    "/js",
    "/build",
}

# Path prefixes that are always public
PUBLIC_PREFIXES = (
    "/storage/",
    "/static/",  # All static files are public (HTML, CSS, JS)
    "/tenant",   # Tenant pages (My Case) - serve page, auth handled by page JS
    "/law-library",  # Law Library page
    "/eviction-defense",  # Eviction Defense page
    "/zoom-court",  # Zoom Court page
    "/api/health",
    "/api/version",
    "/api/roles",  # Role validation API - public for upgrade requests
    # NOTE: ALL other /api/ endpoints REQUIRE storage authentication
    # The frontend pages (/static/*.html) will check auth and redirect
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
    
    # Static assets
    if path.endswith(('.css', '.js', '.png', '.jpg', '.ico', '.svg', '.woff', '.woff2')):
        return True
    
    return False


def is_valid_storage_user(user_id: str) -> bool:
    """
    Validate user ID represents a real user with storage connected.
    
    Valid format: <provider><role><8-char-random>
    Example: GU7x9kM2pQ = Google + User + 7x9kM2pQ
    
    SECURITY: Blocks system users, demo users, and invalid IDs.
    """
    if not user_id:
        return False
    
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
        
        # Get user ID from cookie
        user_id = request.cookies.get(COOKIE_USER_ID)
        
        # Check if valid storage user
        if not is_valid_storage_user(user_id):
            # Log the issue
            import logging
            logger = logging.getLogger("semptify.security")
            
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
                        "redirect_url": "/storage/providers"
                    }
                )
            
            # For HTML pages, redirect to storage providers
            return RedirectResponse(
                url="/storage/providers",
                status_code=302
            )
        
        # Valid user - check permanent completion record before continuing.
        # If "storage_connected" is in completed_groups, the ProcessGroup exit criteria
        # were already verified at OAuth time. No cloud round-trip ever needed again.
        if self.enforce:
            try:
                import logging
                from sqlalchemy import select as _select
                from app.core.database import get_session_factory
                from app.models.models import User as _User

                _factory = get_session_factory()
                async with _factory() as _db:
                    _result = await _db.execute(
                        _select(_User.completed_groups).where(_User.id == user_id)
                    )
                    _row = _result.scalar_one_or_none()
                    if _row is None:
                        # User cookie is valid-format but no DB row — not fully registered yet
                        _logger = logging.getLogger("semptify.security")
                        _logger.warning(
                            "User ID %s has valid format but no DB record — redirecting to storage",
                            user_id[:4] + "***",
                        )
                        if path.startswith("/api/"):
                            return JSONResponse(
                                status_code=401,
                                content={
                                    "error": "storage_required",
                                    "message": "Please connect your cloud storage to continue",
                                    "action": "redirect",
                                    "redirect_url": "/storage/providers",
                                },
                            )
                        return RedirectResponse(url="/storage/providers", status_code=302)

                    completed = _row or ""
                    if "storage_connected" not in completed.split(","):
                        # User row exists but storage_connected not yet written —
                        # Onboarding is incomplete; track redirect attempts
                        
                        # Get current redirect loop count
                        loop_count_str = request.cookies.get(REDIRECT_LOOP_COOKIE, "0")
                        try:
                            loop_count = int(loop_count_str)
                        except ValueError:
                            loop_count = 0
                        
                        # Check if max redirects exceeded
                        if loop_count >= MAX_REDIRECT_LOOPS:
                            # Max redirects reached - show special instructions
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
                            response = RedirectResponse(url="/onboarding/max-redirects", status_code=302)
                            response.delete_cookie(REDIRECT_LOOP_COOKIE)
                            return response
                        
                        # Increment loop count and redirect to welcome screen
                        loop_count += 1
                        
                        if path.startswith("/api/"):
                            return JSONResponse(
                                status_code=401,
                                content={
                                    "error": "onboarding_incomplete",
                                    "message": "Please complete onboarding to continue",
                                    "action": "redirect",
                                    "redirect_url": "/",
                                },
                            )
                        
                        # Redirect to welcome screen
                        response = RedirectResponse(url="/", status_code=302)
                        response.set_cookie(
                            key=REDIRECT_LOOP_COOKIE,
                            value=str(loop_count),
                            max_age=3600,  # 1 hour
                            httponly=True,
                            samesite="lax",
                        )
                        return response

                    # Check client_activated gate — user must have uploaded at least one document
                    # to unlock full Semptify functionality
                    if "client_activated" not in completed.split(","):
                        # User has storage connected but no documents uploaded yet
                        # Allow access to document upload and basic vault operations only
                        if path.startswith("/api/documents/upload") or path.startswith("/api/vault/upload"):
                            # Allow document uploads to activate the client
                            pass
                        elif path.startswith("/api/") and not (
                            path.startswith("/api/health") or
                            path.startswith("/api/version") or
                            path.startswith("/api/roles")
                        ):
                            # Block most API endpoints until client activation
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "error": "client_activation_required",
                                    "message": "Please upload your first document to activate your Semptify account",
                                    "action": "redirect",
                                    "redirect_url": "/documents",
                                },
                            )
                        elif not path.startswith("/static/") and not path.startswith("/documents"):
                            # Block most HTML pages until client activation
                            return RedirectResponse(url="/documents", status_code=302)

            except Exception:
                # If DB is unavailable, fall through — don't block the user on a DB error.
                # This degrades gracefully: format validation still passed above.
                pass

        return await call_next(request)
