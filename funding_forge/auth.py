"""Funding Forge admin authentication.

Self-contained admin gate using a signed cookie. Credentials are read from the
Funding Forge .env (FUNDING_FORGE_ADMIN_*) or from the main Semptify admin
credentials (ADMIN_*). Optional TOTP via ADMIN_TOTP_SECRET or
FUNDING_FORGE_ADMIN_TOTP_SECRET.

This module does NOT import the main Semptify app so Funding Forge remains
standalone.
"""

import hmac
import logging
from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

try:
    import pyotp

    HAS_PYOTP = True
except ImportError:
    HAS_PYOTP = False

from funding_forge.config import settings

logger = logging.getLogger("funding_forge.auth")

COOKIE_NAME = "funding_forge_admin"
HEADER_NAME = "x-admin-token"

token_header = APIKeyHeader(name=HEADER_NAME, auto_error=False)


def admin_auth_enabled() -> bool:
    """Return True when admin credentials are configured."""
    return bool(settings.admin_username and settings.admin_password)


@lru_cache(maxsize=1)
def _expected_token() -> str:
    """Derive a stable admin token from the configured password."""
    if not settings.admin_password:
        return ""
    return hmac.new(
        settings.admin_password.encode(),
        f"funding_forge_admin:{settings.admin_username}".encode(),
        "sha256",
    ).hexdigest()


def create_admin_token() -> str:
    """Create the admin token to be stored in a cookie/header."""
    return _expected_token()


def verify_admin_token(token: str | None) -> bool:
    """Constant-time comparison of the provided admin token."""
    if not token or not admin_auth_enabled():
        return False
    expected = _expected_token()
    if not expected:
        return False
    return hmac.compare_digest(token, expected)


def verify_admin_credentials(username: str, password: str, totp_code: str | None = None) -> bool:
    """Validate username/password and optional TOTP."""
    if not admin_auth_enabled():
        return True
    if username != settings.admin_username:
        return False
    if password != settings.admin_password:
        return False

    if settings.admin_totp_secret:
        if not HAS_PYOTP:
            logger.warning("TOTP secret configured but pyotp is not installed")
            return False
        if not totp_code:
            return False
        if not pyotp.TOTP(settings.admin_totp_secret).verify(totp_code, valid_window=1):
            return False

    return True


def get_admin_token_from_request(request: Request) -> str | None:
    """Read admin token from cookie or header."""
    return request.cookies.get(COOKIE_NAME) or request.headers.get(HEADER_NAME)


def admin_dependency(request: Request, token: str | None = Depends(token_header)) -> bool:
    """FastAPI dependency to enforce admin authentication."""
    token = token or get_admin_token_from_request(request)
    if not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )
    return True
