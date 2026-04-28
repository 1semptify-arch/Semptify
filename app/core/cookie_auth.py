"""
Semptify 5.0 - Cookie Authentication
HMAC-signed user ID cookie: tamper-proof, zero overhead, no database hit.

Format:  <user_id>.<hmac_signature>
Example: GU7x9kM2pQ.a3f8c2d1e4b7...

sign_user_id()   — called once at OAuth callback (cookie write)
verify_user_id() — called at every cookie read (middleware, guards, routes)

If SECRET_KEY changes, all existing cookies become invalid and users
are re-routed to /storage/providers to re-authenticate. Expected behavior.
"""

import hashlib
import hmac
import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SEPARATOR = "."


def _get_secret() -> bytes:
    """Return SECRET_KEY as bytes."""
    return get_settings().secret_key.encode("utf-8")


def sign_user_id(user_id: str) -> str:
    """
    Sign a user_id and return the cookie value.
    Returns: "<user_id>.<hmac_hex>"
    """
    if not user_id:
        raise ValueError("user_id cannot be empty")
    sig = hmac.new(_get_secret(), user_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{user_id}{_SEPARATOR}{sig}"


def verify_user_id(cookie_value: Optional[str]) -> Optional[str]:
    """
    Verify a signed cookie value and return the raw user_id if valid.

    Returns:
        user_id string if signature is valid
        None if cookie is missing, malformed, or tampered
    """
    if not cookie_value:
        return None

    parts = cookie_value.rsplit(_SEPARATOR, 1)
    if len(parts) != 2:
        logger.warning("cookie_auth: malformed cookie (no separator)")
        return None

    user_id, provided_sig = parts[0], parts[1]

    if not user_id or not provided_sig:
        logger.warning("cookie_auth: empty user_id or signature")
        return None

    expected_sig = hmac.new(
        _get_secret(), user_id.encode("utf-8"), hashlib.sha256
    ).hexdigest()  # noqa: S324

    if not hmac.compare_digest(expected_sig, provided_sig):
        logger.warning(
            "cookie_auth: signature mismatch for user_id prefix=%s",
            user_id[:4] + "***",
        )
        return None

    return user_id


def extract_user_id(request) -> Optional[str]:
    """
    Convenience: read and verify semptify_uid from a FastAPI Request.
    Returns raw user_id or None.
    """
    from app.core.user_id import COOKIE_USER_ID
    raw = request.cookies.get(COOKIE_USER_ID)
    return verify_user_id(raw)


def set_auth_cookie(
    response,
    user_id: str,
    max_age: int = 365 * 24 * 60 * 60,
    secure: bool = False,
) -> None:
    """
    Single issuing authority for the semptify_uid cookie.

    ALL cookie writes in the application MUST go through this function.
    Never call response.set_cookie(key="semptify_uid", ...) directly.

    Signs the user_id with HMAC before writing. Verification happens in
    verify_user_id() / is_valid_storage_user() on every subsequent request.

    Args:
        response:  FastAPI Response or RedirectResponse object
        user_id:   Raw user_id (unsigned) — will be signed here
        max_age:   Cookie lifetime in seconds (default 1 year)
        secure:    True in production (HTTPS), False for localhost HTTP
    """
    from app.core.user_id import COOKIE_USER_ID
    response.set_cookie(
        key=COOKIE_USER_ID,
        value=sign_user_id(user_id),
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="lax",
    )
