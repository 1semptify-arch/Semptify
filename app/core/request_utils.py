"""
Shared Request Utilities
========================

Centralises repeated request-handling patterns that were duplicated
across dozens of router modules:

1. **get_request_user_id(request)** -- verifies the HMAC-signed
   ``semptify_uid`` cookie (via ``cookie_auth.extract_user_id``) and
   returns the raw user ID, or ``"anonymous"`` when the cookie is
   absent or fails verification.

2. **require_request_user_id(request)** -- same verification but raises
   ``HTTPException(401)`` when the cookie is missing, unsigned, or
   tampered, for endpoints that must have an authenticated user.

3. **raise_for_storage_error(exc)** -- inspects an exception from a
   storage operation and re-raises as the appropriate ``HTTPException``
   (401 / 403 / 500), eliminating the duplicated if/elif/else blocks
   in ``vault/router.py`` and elsewhere.
"""

import logging
from typing import NoReturn

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def get_request_user_id(request: Request, *, fallback: str = "anonymous") -> str:
    """Return the verified user ID from the request cookie, or *fallback*.

    The ``semptify_uid`` cookie is HMAC-signed (``<user_id>.<sig>``). This
    verifies the signature and returns the raw user_id — never the signed
    value, which would poison DB lookups and leak the signature into UI.
    """
    from app.core.cookie_auth import extract_user_id

    return extract_user_id(request) or fallback


def require_request_user_id(request: Request) -> str:
    """Return the verified user ID or raise 401 if the cookie is missing,
    unsigned, or has an invalid signature."""
    from app.core.cookie_auth import extract_user_id

    user_id = extract_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


def raise_for_storage_error(exc: Exception, *, default_detail: str = "Storage error") -> NoReturn:
    """Translate a storage-layer exception into an ``HTTPException``.

    Call this inside the ``except`` block that wraps a storage
    operation.  It inspects the stringified error for common
    auth/permission keywords and raises the matching HTTP status:

    * 401 -- authentication / token problems
    * 403 -- permission / forbidden problems
    * 500 -- everything else
    """
    error_msg = str(exc)
    if "401" in error_msg or "Unauthorized" in error_msg or "access" in error_msg.lower():
        raise HTTPException(
            status_code=401,
            detail=f"Storage authentication failed: {error_msg}",
        )
    if "403" in error_msg or "Forbidden" in error_msg:
        raise HTTPException(
            status_code=403,
            detail=f"Storage access denied: {error_msg}",
        )
    raise HTTPException(
        status_code=500,
        detail=f"{default_detail}: {error_msg}",
    )
