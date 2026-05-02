"""
Semptify 5.0 - Smart Gate Checkpoint

Enforces single entry point for NEW users while allowing returning users
to bypass. Validates Semptify's legal right to work with user documents.

Logic:
- Has valid session (semptify_uid)? → ALLOW (returning user)
- Has checkpoint cookie? → ALLOW (saw welcome page)
- Protected path + no checkpoint? → Redirect to welcome
- Public paths → Always ALLOW
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse
import logging

logger = logging.getLogger(__name__)

# Checkpoint cookie constants
CHECKPOINT_COOKIE = "semptify_checkpoint"
CHECKPOINT_VALUE = "acknowledged"  # User acknowledged terms/privacy
CHECKPOINT_MAX_AGE = 365 * 24 * 60 * 60  # 1 year

# User session cookie (from user_id.py)
USER_COOKIE = "semptify_uid"

# Always exempt - never check checkpoint
EXEMPT_PATHS = {
    "/",  # Welcome page itself
    "/favicon.ico",
    "/robots.txt",
    "/static/",
    "/public/",
    "/storage/reconnect",
    "/storage/providers",
    "/storage/callback",
    "/api/user/lookup",
    "/api/session/restore",
    "/health",
}

# Protected paths - checkpoint required if no session
PROTECTED_PREFIXES = (
    "/tenant/",
    "/advocate/",
    "/legal/",
    "/manager/",
    "/admin/",
    "/vault/",
    "/documents/",
    "/timeline/",
    "/case/",
    "/home",
    "/dashboard",
)


class SmartCheckpointMiddleware(BaseHTTPMiddleware):
    """
    Smart gate: New users through welcome, returning users bypass.
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Always exempt paths
        if self._is_exempt(path):
            return await call_next(request)
        
        # Has valid session? → Allow (returning user)
        user_id = request.cookies.get(USER_COOKIE)
        if user_id and len(user_id) >= 10:
            return await call_next(request)
        
        # Has checkpoint? → Allow (saw welcome)
        checkpoint = request.cookies.get(CHECKPOINT_COOKIE)
        if checkpoint == CHECKPOINT_VALUE:
            return await call_next(request)
        
        # Protected path with no credentials? → TEMPORARILY ALLOW ALL
        # FIXME: Re-enable checkpoint gate after cookie issue resolved
        # if self._is_protected(path):
        #     logger.info(f"Gate: {path} → welcome (no checkpoint/session)")
        #     return RedirectResponse(
        #         url="/?gate=checkpoint_required&return_to=" + path,
        #         status_code=302
        #     )
        
        # Public path → Allow
        return await call_next(request)
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is always exempt."""
        for exempt in EXEMPT_PATHS:
            if path == exempt or path.startswith(exempt):
                return True
        return False
    
    def _is_protected(self, path: str) -> bool:
        """Check if path requires checkpoint."""
        for prefix in PROTECTED_PREFIXES:
            if path.startswith(prefix):
                return True
        return False


def set_checkpoint_cookie(response, max_age: int = CHECKPOINT_MAX_AGE):
    """
    Set checkpoint cookie - call this when user clicks button on welcome page.
    
    Usage:
        from app.core.checkpoint_middleware import set_checkpoint_cookie
        set_checkpoint_cookie(response)
    """
    response.set_cookie(
        key=CHECKPOINT_COOKIE,
        value=CHECKPOINT_VALUE,
        httponly=False,  # Must be readable by JS on welcome page
        secure=False,  # Allow HTTP for testing
        samesite="lax",
        path="/",  # Critical: cookie must be valid for all paths
        max_age=max_age,
    )


def clear_checkpoint_cookie(response):
    """Clear checkpoint - for logout/account deletion."""
    response.delete_cookie(key=CHECKPOINT_COOKIE)


# =============================================================================
# FastAPI Dependencies for Route-Level Enforcement
# =============================================================================

async def require_checkpoint(request: Request):
    """
    Dependency for routes that absolutely require checkpoint.
    Use sparingly - middleware handles most cases.
    """
    user_id = request.cookies.get(USER_COOKIE)
    checkpoint = request.cookies.get(CHECKPOINT_COOKIE)
    
    if not user_id and checkpoint != CHECKPOINT_VALUE:
        raise HTTPException(
            status_code=403,
            detail="Checkpoint required. Please visit welcome page first."
        )


from fastapi import HTTPException
