"""
Semptify 5.0 - Cookie Authentication
HMAC-signed user ID cookie: tamper-proof, zero overhead, no database hit.

Format:  <user_id>.<hmac_signature>
Example: GU7x9kM2pQ.a3f8c2d1e4b7...

sign_user_id()   — called once at OAuth callback (cookie write)
verify_user_id() — called at every cookie read (middleware, guards, routes)

On SECRET_KEY rotation, cookies signed with a retired key keep verifying
for the SECRET_KEY_HISTORY grace window (60 days), then users are re-routed
to /storage/providers to re-authenticate. Expected behavior.
"""

import logging

from app.core.key_derivation import hmac_sign_user_id, hmac_verify_user_id

logger = logging.getLogger(__name__)

_SEPARATOR = "."


def sign_user_id(user_id: str) -> str:
    """
    Sign a user_id and return the cookie value.
    Returns: "<user_id>.<hmac_hex>"
    Always signs with the CURRENT SECRET_KEY version.
    """
    if not user_id:
        raise ValueError("user_id cannot be empty")
    return f"{user_id}{_SEPARATOR}{hmac_sign_user_id(user_id)}"


def verify_user_id(cookie_value: str | None) -> str | None:
    """
    Verify a signed cookie value and return the raw user_id if valid.

    Returns:
        user_id string if signature is valid
        None if cookie is missing, malformed, or tampered
    """
    # Ensure cookie_value is a string (not a Cookie object)
    cookie_str = str(cookie_value) if cookie_value is not None else None
    if not cookie_str:
        return None

    parts = cookie_str.rsplit(_SEPARATOR, 1)
    if len(parts) != 2:
        logger.warning("cookie_auth: malformed cookie (no separator)")
        return None

    user_id, provided_sig = parts[0], parts[1]

    if not user_id or not provided_sig:
        logger.warning("cookie_auth: empty user_id or signature")
        return None

    # Verify against the current key, then valid SECRET_KEY_HISTORY entries
    # (60-day grace window per the vault-security spec).
    if not hmac_verify_user_id(user_id, provided_sig):
        logger.warning(
            "cookie_auth: signature mismatch for user_id prefix=%s",
            user_id[:4] + "***",
        )
        return None

    return user_id


def extract_user_id(request) -> str | None:
    """
    Convenience: read and verify semptify_uid from a FastAPI Request.
    Returns raw user_id or None.
    """
    from app.core.user_id import COOKIE_USER_ID

    _raw = request.cookies.get(COOKIE_USER_ID)
    raw = str(_raw) if _raw is not None else None
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
        path="/",
        httponly=False,
        secure=secure,
        samesite="lax",
    )


def clear_auth_cookie(response):
    """Clear the authentication cookie."""
    from app.core.user_id import COOKIE_USER_ID

    response.delete_cookie(
        key=COOKIE_USER_ID,
        path="/",
        httponly=False,
        secure=True,  # Assume secure for deletion
        samesite="lax",
    )
