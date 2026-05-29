"""
Semptify Auth SDK — Cookie Auth
================================
HMAC-signed user ID cookie: tamper-proof, zero overhead, no database hit.

Format:  <user_id>.<hmac_signature>
Example: GU7x9kM2pQ.a3f8c2d1e4b7...

Zero framework dependencies in the core logic.
Framework-specific helpers (set_auth_cookie) accept a response object generically.

Wraps app.core.cookie_auth — single source of truth stays in core.
"""

from typing import Optional
from app.core.cookie_auth import sign_user_id, verify_user_id


COOKIE_NAME = "semptify_uid"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


class CookieAuth:
    """
    Stateless HMAC cookie auth helper.

    Usage:
        auth = CookieAuth(secret_key="your-secret")
        signed = auth.sign("GU7x9kM2pQ")
        user_id = auth.verify(cookie_value)  # None if tampered
    """

    def sign(self, user_id: str) -> str:
        """Sign a user_id for cookie storage."""
        return sign_user_id(user_id)

    def verify(self, cookie_value: Optional[str]) -> Optional[str]:
        """Verify cookie and return raw user_id, or None if invalid."""
        return verify_user_id(cookie_value)


def set_auth_cookie(response, user_id: str, secure: bool = True) -> str:
    """
    Set the HMAC-signed auth cookie on a response object.

    Works with FastAPI Response, Starlette Response, or any object
    with a set_cookie() method.

    Returns the signed cookie value.
    """
    signed = sign_user_id(user_id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=signed,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=secure,
        samesite="lax",
    )
    return signed


def verify_auth_cookie(cookie_value: Optional[str]) -> Optional[str]:
    """
    Verify a semptify_uid cookie value.

    Returns raw user_id if valid, None if missing/tampered.
    """
    return verify_user_id(cookie_value)
