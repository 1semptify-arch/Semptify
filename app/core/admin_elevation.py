"""
Admin Elevation — Temporary privilege escalation on top of an existing OAuth session.

Admin is NOT a role. It is a time-limited elevation granted after TOTP verification.

Flow:
    1. User connects OAuth normally (tenant/manager/any role)
    2. User navigates to /admin/* — elevation check fires
    3. If no valid elevation cookie → redirect to /admin/login (inline prompt)
    4. User enters password + TOTP → elevation cookie issued (4 hours)
    5. Elevation expires → user falls back to normal OAuth session automatically

Cookie format:
    semptify_admin_elev = <payload_b64>.<hmac_hex>
    payload = base64(json({"issued_at": int, "expires_at": int, "uid": str}))

Security:
    - HMAC-SHA256 signed with SECRET_KEY — cannot be forged
    - Short TTL (4 hours default) — stolen cookie has limited window
    - Requires BOTH valid OAuth session AND valid elevation cookie
    - TOTP required every elevation — no long-lived admin sessions
"""

import base64
import hashlib
import hmac
import json
import logging
from typing import Optional

from app.core.config import get_settings
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

ELEVATION_COOKIE_NAME = "semptify_admin_elev"
ELEVATION_TTL_SECONDS = 4 * 60 * 60  # 4 hours
_SEPARATOR = "."


def _get_secret() -> bytes:
    return (get_settings().secret_key + ":admin_elevation").encode("utf-8")


def issue_elevation_cookie(user_id: str) -> str:
    """
    Issue a signed admin elevation cookie value.

    Args:
        user_id: The OAuth user_id of the user being elevated (for audit)

    Returns:
        Signed cookie value string ready to set on response.
    """
    now = int(utc_now().timestamp())
    payload = {
        "issued_at": now,
        "expires_at": now + ELEVATION_TTL_SECONDS,
        "uid": user_id,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    sig = hmac.new(_get_secret(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}{_SEPARATOR}{sig}"


def verify_elevation_cookie(cookie_value: Optional[str]) -> Optional[dict]:
    """
    Verify a signed elevation cookie and return the payload if valid and not expired.

    Returns:
        dict with {"issued_at", "expires_at", "uid"} if valid
        None if missing, malformed, tampered, or expired
    """
    if not cookie_value:
        return None

    cookie_str = str(cookie_value)
    parts = cookie_str.rsplit(_SEPARATOR, 1)
    if len(parts) != 2:
        logger.warning("admin_elevation: malformed cookie")
        return None

    payload_b64, provided_sig = parts[0], parts[1]

    expected_sig = hmac.new(
        _get_secret(), payload_b64.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, provided_sig):
        logger.warning("admin_elevation: signature mismatch — possible tampering")
        return None

    try:
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
    except Exception as exc:
        logger.warning("admin_elevation: payload decode failed: %s", exc)
        return None

    now = int(utc_now().timestamp())
    if payload.get("expires_at", 0) < now:
        logger.info("admin_elevation: elevation cookie expired for uid=%s", str(payload.get("uid", ""))[:6])
        return None

    return payload


def set_elevation_cookie(response, user_id: str) -> None:
    """Set the admin elevation cookie on a response."""
    value = issue_elevation_cookie(user_id)
    response.set_cookie(
        key=ELEVATION_COOKIE_NAME,
        value=value,
        max_age=ELEVATION_TTL_SECONDS,
        path="/admin",
        httponly=True,
        secure=True,
        samesite="strict",
    )
    logger.info("admin_elevation: elevation granted for uid=%s (4 hours)", user_id[:6])


def clear_elevation_cookie(response) -> None:
    """Clear the admin elevation cookie."""
    response.delete_cookie(
        key=ELEVATION_COOKIE_NAME,
        path="/admin",
        httponly=True,
        secure=True,
        samesite="strict",
    )
