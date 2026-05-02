"""
SSOT Guard — Runtime enforcement of Single Source of Truth.

This module provides active defense against SSOT violations:
- Detects hardcoded URLs at runtime
- Blocks non-SSOT navigation attempts
- Logs violations for audit

Principle: Bypass attempts fail loudly, not silently.
"""
import re
import logging
from functools import wraps
from typing import Set, Callable, Any
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from app.core.navigation import navigation

logger = logging.getLogger(__name__)

# Canonical paths from SSOT — these are the ONLY valid destinations
SSOT_CANONICAL_PATHS: Set[str] = set()


def _build_canonical_set():
    """Build set of all SSOT-approved paths."""
    global SSOT_CANONICAL_PATHS
    paths = set()
    
    # Onboarding flow paths
    for stage in navigation.ONBOARDING_FLOW.values():
        paths.add(stage.path)
    
    # Main nav paths
    for item in navigation.MAIN_NAV:
        paths.add(item.path)
    
    # Entry points
    paths.add("/")
    paths.add(navigation.get_onboarding_start())
    paths.add(navigation.get_reconnect_flow())
    paths.add("/home")
    
    SSOT_CANONICAL_PATHS = paths
    return paths


def is_ssot_path(path: str) -> bool:
    """Check if a path is in the SSOT registry."""
    if not SSOT_CANONICAL_PATHS:
        _build_canonical_set()
    return path in SSOT_CANONICAL_PATHS


def detect_hardcoded_url(value: str) -> bool:
    """Detect potential hardcoded URLs in strings."""
    patterns = [
        r'["\']/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+\.html["\']',  # /path/file.html
        r'["\']/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+["\']',        # /path/route
        r'window\.location\.href\s*=\s*["\'][^"\']+["\']',  # JS redirects
    ]
    for pattern in patterns:
        if re.search(pattern, value):
            return True
    return False


class SSOTViolation(Exception):
    """Raised when code attempts to bypass SSOT navigation."""
    pass


def require_ssot_path(path: str, context: str = ""):
    """
    Validate a path is SSOT-compliant.
    
    Args:
        path: The URL path to validate
        context: Description of where this check is occurring
        
    Raises:
        SSOTViolation: If path is not in SSOT registry
    """
    if not is_ssot_path(path):
        violation_msg = f"SSOT VIOLATION: Non-canonical path '{path}' used in {context}. " \
                     f"Use navigation.get_stage() or navigation.get_onboarding_start() instead."
        logger.error(violation_msg)
        raise SSOTViolation(violation_msg)


def ssot_redirect(path: str, context: str = "", strict: bool = False) -> RedirectResponse:
    """
    Create a redirect response with SSOT validation.
    
    All redirects in the app should use this instead of raw RedirectResponse.
    
    Args:
        path: Destination path
        context: Where this redirect originates
        strict: If True, raises on non-SSOT paths. If False, warns and allows.
        
    Returns:
        RedirectResponse (validated through evolution system)
        
    Raises:
        SSOTViolation: Only if strict=True and path is non-canonical
    """
    # Use evolution system - paths can grow and change
    resolved = navigation.resolve_path(path)
    
    if resolved != path:
        # Path was deprecated or escaped - log the transformation
        logger.info(f"SSOT Evolution: '{path}' resolved to '{resolved}' in {context}")
        path = resolved
    elif not is_ssot_path(path):
        # Non-SSOT path - warn but allow (evolution needs experimentation)
        logger.warning(f"SSOT Advisory: Non-canonical path '{path}' used in {context}. "
                      f"Consider adding to registry via register_stage().")
        if strict:
            raise SSOTViolation(f"Strict mode: Non-canonical path '{path}' blocked in {context}")
    
    return RedirectResponse(url=path, status_code=302)


def ssot_middleware_guard(request: Request) -> None:
    """
    Middleware-level SSOT check.
    
    Validates that redirect targets in request state are SSOT-compliant.
    Call this in middleware that handles redirects.
    """
    # Check if this request is part of a redirect chain
    referer = request.headers.get("referer", "")
    
    # Log non-SSOT referers for audit
    if referer and not any(p in referer for p in SSOT_CANONICAL_PATHS):
        if "/api/" not in str(request.url):  # Skip API calls
            logger.warning(f"SSOT AUDIT: Request from non-canonical referer: {referer}")


# =============================================================================
# Enforcement Decorators
# =============================================================================

def enforce_ssot_paths(func: Callable) -> Callable:
    """
    Decorator: Validates all RedirectResponse returns are SSOT-compliant.
    
    Usage:
        @router.get("/route")
        @enforce_ssot_paths
        async def my_route():
            return RedirectResponse(url="/forbidden")  # Raises SSOTViolation
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        
        if isinstance(result, RedirectResponse):
            location = result.headers.get("location", "")
            if location and not is_ssot_path(location):
                raise SSOTViolation(
                    f"SSOT VIOLATION in {func.__name__}: "
                    f"Redirect to non-canonical path '{location}'. "
                    f"Use navigation registry instead."
                )
        
        return result
    
    return wrapper


def audit_hardcoded_urls(func: Callable) -> Callable:
    """
    Decorator: Logs potential hardcoded URLs in string returns.
    
    For HTML/string responses that might contain inline JS with hardcoded paths.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        
        if isinstance(result, str) and len(result) > 100:
            # Check for hardcoded URLs in HTML/JS
            if detect_hardcoded_url(result):
                logger.warning(
                    f"SSOT AUDIT: {func.__name__} may contain hardcoded URLs. "
                    f"Review for SSOT compliance."
                )
        
        return result
    
    return wrapper
