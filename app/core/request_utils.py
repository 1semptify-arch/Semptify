"""
Shared Request Utilities
========================

Centralises repeated request-handling patterns that were duplicated
across dozens of router modules:

1. **get_request_user_id(request)** -- extracts the user ID from the
   ``semptify_uid`` cookie (via the canonical ``COOKIE_USER_ID``
   constant), returning ``"anonymous"`` when the cookie is absent.

2. **require_request_user_id(request)** -- same extraction but raises
   ``HTTPException(401)`` when the cookie is missing, for endpoints
   that must have an authenticated user.

3. **raise_for_storage_error(exc)** -- inspects an exception from a
   storage operation and re-raises as the appropriate ``HTTPException``
   (401 / 403 / 500), eliminating the duplicated if/elif/else blocks
   in ``vault/router.py`` and elsewhere.
"""

import logging
from typing import NoReturn

from fastapi import HTTPException, Request

from app.core.user_id import COOKIE_USER_ID

logger = logging.getLogger(__name__)


def get_request_user_id(request: Request, *, fallback: str = "anonymous") -> str:
    """Return the user ID from the request cookie, or *fallback*."""
    return request.cookies.get(COOKIE_USER_ID, fallback)


def require_request_user_id(request: Request) -> str:
    """Return the user ID or raise 401 if the cookie is missing."""
    user_id = request.cookies.get(COOKIE_USER_ID)
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
