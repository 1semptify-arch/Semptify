"""Public surface router — stateless landing and i18n endpoints.

These routes are intentionally public and session-free. They support the
semptify.org landing page and locale preference.
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.i18n import SUPPORTED_LOCALES, get_locale, i18n
from app.core.ssot_guard import ssot_redirect
from app.modules.context_engine.cache import get_verified_landing_facts

router = APIRouter(tags=["Public Surface"])


@router.get("/api/landing/facts", include_in_schema=False)
async def landing_facts_api():
    """Public endpoint returning verified, non-expired landing/public facts.

    Unverified or expired claims are omitted; the landing page auto-hides them.
    """
    facts = await get_verified_landing_facts()
    return [
        {
            "claim": f.claim,
            "citation": f.citation,
            "source_url": f.source_url,
            "source_name": f.source_name,
            "canonical_value": f.canonical_value,
            "verified_at": f.verified_at.isoformat() if f.verified_at else None,
            "expires_at": f.expires_at.isoformat() if f.expires_at else None,
        }
        for f in facts
    ]


@router.get("/api/i18n/locale", include_in_schema=False)
async def get_current_locale(request: Request):
    """Return the resolved locale and supported locale list for JS."""
    return JSONResponse(
        {
            "locale": i18n.get_locale(request),
            "supported_locales": SUPPORTED_LOCALES,
        }
    )


@router.post("/api/i18n/set-locale", include_in_schema=False)
async def set_locale(request: Request, locale: str = Form(...)):
    """Set the `semptify_locale` cookie and return the user to their prior page."""
    if locale not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=400, detail="Unsupported locale")

    referer = request.headers.get("referer", "/")
    target_path = urlparse(referer).path or "/"
    response = ssot_redirect(target_path, context="i18n.set-locale", strict=False)

    # Mirrors cookie settings used by cookie_auth for consistency.
    secure = request.url.scheme == "https"
    response.set_cookie(
        key="semptify_locale",
        value=locale,
        max_age=365 * 24 * 60 * 60,
        path="/",
        samesite="lax",
        secure=secure,
        httponly=False,
    )
    return response
