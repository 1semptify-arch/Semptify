"""
Google Cross-Account Protection (RISC) webhook endpoint.

Google sends Security Event Tokens (SETs) here when:
- A user's Google account is compromised
- A user revokes access to this app
- A user's session is invalidated

Spec: https://developers.google.com/identity/protocols/risc
RFC:  https://tools.ietf.org/html/rfc8417 (Security Event Tokens)

When Google fires an event, we:
1. Verify the JWT signature using Google's RISC public keys
2. Parse the event type
3. Act: revoke session, delete cookie, log the event

This endpoint must be registered in Google Cloud Console:
  APIs & Services ▸ OAuth consent screen ▸ Cross-Account Protection
  Receiver endpoint URL: https://semptify-jsam.onrender.com/risc/google/webhook
"""
# Migrated from app/routers/risc.py into the risc SDK module.
# All imports remain absolute since risc is a CORE module.

import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jose import JWTError, jwt

from app.core.security import auth_gate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/risc/google",
    tags=["RISC"],
    dependencies=[Depends(auth_gate)],
)

# Google's RISC issuer and JWKS endpoint
_GOOGLE_RISC_ISSUER = "https://accounts.google.com"
_GOOGLE_RISC_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

# Cached JWKS (refreshed on demand)
_jwks_cache: dict | None = None
_jwks_cache_at: float = 0.0
_JWKS_TTL = 3600  # 1 hour


async def _get_google_jwks() -> dict:
    """Fetch and cache Google's public JWKS for RISC token verification."""
    global _jwks_cache, _jwks_cache_at
    now = time.monotonic()
    if _jwks_cache and (now - _jwks_cache_at) < _JWKS_TTL:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(_GOOGLE_RISC_JWKS_URL)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_at = now
        return _jwks_cache


_MAX_TOKEN_AGE_SECONDS = 300  # 5 minutes — reject replayed tokens


async def _verify_risc_token(token: str, audience: str) -> dict:
    """
    Verify a Google RISC Security Event Token (SET).
    Returns the decoded payload if valid, raises HTTPException if not.
    """
    try:
        jwks = await _get_google_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=audience,
            issuer=_GOOGLE_RISC_ISSUER,
        )

        # Replay attack prevention: reject tokens older than 5 minutes
        iat = payload.get("iat")
        if iat is not None:
            age = time.time() - float(iat)
            if age > _MAX_TOKEN_AGE_SECONDS:
                logger.warning("RISC token rejected: too old (age=%.0fs)", age)
                raise HTTPException(status_code=400, detail="RISC token expired")

        return payload
    except JWTError as exc:
        logger.warning("RISC token verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid RISC token")


async def _revoke_user_session(google_subject: str) -> None:
    """
    Revoke all sessions for a user identified by their Google subject ID.
    Looks up by storage_user_id (which stores the Google subject).
    """
    try:
        from sqlalchemy import delete, select

        from app.core.database import get_session_factory
        from app.models.models import StorageSession, User

        factory = get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(User).where(
                    User.primary_provider == "google_drive",
                    User.storage_user_id == google_subject,
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                logger.info("RISC: no user found for Google subject %s", google_subject[:8] + "***")
                return

            # Delete all sessions for this user
            await db.execute(
                delete(StorageSession).where(StorageSession.user_id == user.id)
            )
            await db.commit()

            # Evict from token cache
            from app.core.oauth_token_manager import token_manager
            token_manager.revoke(user.id)

            logger.warning(
                "RISC: session revoked for user %s (Google subject %s)",
                user.id[:6] + "***",
                google_subject[:8] + "***",
            )
    except Exception as exc:
        logger.exception("RISC: failed to revoke session for subject %s: %s", google_subject[:8] + "***", exc)


@router.post("/webhook")
async def risc_webhook(request: Request) -> Response:
    """
    Receive Google Cross-Account Protection Security Event Tokens.

    Google POSTs a JWT (Security Event Token) when a security event occurs.
    We verify the signature and act on the event type.
    """
    # Read raw body (JWT is sent as plain text, not JSON)
    body = await request.body()
    token = body.decode("utf-8").strip()

    if not token:
        raise HTTPException(status_code=400, detail="Empty body")

    # Audience must match our app's client ID
    from app.core.config import get_settings
    settings = get_settings()
    audience = settings.google_drive_client_id

    if not audience:
        logger.error("RISC: GOOGLE_DRIVE_CLIENT_ID not configured — cannot verify token")
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    payload = await _verify_risc_token(token, audience)

    # Extract subject and events
    subject_identifier = payload.get("sub") or (
        payload.get("subject", {}).get("sub")
    )
    events = payload.get("events", {})

    logger.info("RISC event received: subject=%s events=%s",
                (subject_identifier or "?")[:8] + "***", list(events.keys()))

    # Handle each event type
    # https://developers.google.com/identity/protocols/risc#supported_event_types
    handled = False

    if "https://schemas.openid.net/secevent/risc/event-type/sessions-revoked" in events:
        # All sessions revoked (e.g. user changed password)
        if subject_identifier:
            await _revoke_user_session(subject_identifier)
        handled = True

    if "https://schemas.openid.net/secevent/risc/event-type/account-disabled" in events:
        # Account disabled or suspended
        if subject_identifier:
            await _revoke_user_session(subject_identifier)
        handled = True

    if "https://schemas.openid.net/secevent/risc/event-type/account-purged" in events:
        # Account deleted from Google
        if subject_identifier:
            await _revoke_user_session(subject_identifier)
        handled = True

    if "https://schemas.openid.net/secevent/risc/event-type/credential-compromise" in events:
        # Credentials compromised
        if subject_identifier:
            await _revoke_user_session(subject_identifier)
        handled = True

    if "https://schemas.openid.net/secevent/oauth/event-type/tokens-revoked" in events:
        # OAuth tokens explicitly revoked by user (disconnected app)
        if subject_identifier:
            await _revoke_user_session(subject_identifier)
        handled = True

    if not handled:
        logger.info("RISC: unhandled event types: %s", list(events.keys()))

    # Google expects 202 Accepted (not 200)
    return Response(status_code=202)


@router.get("/webhook")
async def risc_webhook_verify(request: Request) -> Response:
    """
    Google verification GET request — returns 200 to confirm endpoint ownership.
    Google may GET this URL to verify it's reachable before activating RISC.
    """
    logger.info("RISC: webhook verification ping received")
    return Response(content="OK", status_code=200)
