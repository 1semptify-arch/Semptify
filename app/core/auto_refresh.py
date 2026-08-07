"""
Automatic Token Refresh - Silent Background Reconnect

This module provides silent background token refresh for returning users.
If refresh succeeds, the user stays on their current page.
If refresh fails, the user is redirected to full reauth flow.

Contract:
- Minimal user interaction (silent background refresh)
- Session preservation (user stays on current page)
- Fallback to full reauth only when refresh fails
"""

import logging
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.oauth_token_manager import OAuthToken, token_manager
from app.core.user_id import parse_user_id
from app.models.models import Session as SessionModel

logger = logging.getLogger(__name__)


class RefreshResult:
    """Result of a token refresh attempt."""
    SUCCESS = "success"
    NO_REFRESH_TOKEN = "no_refresh_token"
    REFRESH_FAILED = "refresh_failed"
    USER_NOT_FOUND = "user_not_found"
    PROVIDER_ERROR = "provider_error"


async def ensure_valid_token(
    user_id: str,
    db: AsyncSession | None = None
) -> tuple[bool, OAuthToken | None, str]:
    """
    Ensure the user has a valid access token, refreshing if needed.
    
    Returns:
        (is_valid, token, status_code)
        - is_valid: True if token is valid (fresh or refreshed)
        - token: The valid OAuthToken, or None if unavailable
        - status_code: One of RefreshResult constants
    """
    # Check in-memory cache first
    cached_token = token_manager.get_token(user_id)
    if cached_token and not cached_token.is_expired():
        logger.debug(f"Token valid in cache for user {user_id[:6]}***")
        return True, cached_token, RefreshResult.SUCCESS

    # Token not in cache or expired - try to refresh from DB
    if not db:
        factory = get_session_factory()
        async with factory() as session:
            return await _refresh_from_db(user_id, session)
    else:
        return await _refresh_from_db(user_id, db)


def _derive_key(user_id: str) -> bytes:
    """Derive encryption key from user_id + server secret."""
    import hashlib

    from app.core.config import get_settings
    settings = get_settings()
    secret_key = getattr(settings, "secret_key", None) or getattr(settings, "SECRET_KEY", "")
    combined = f"{secret_key}:{user_id}".encode()
    return hashlib.sha256(combined).digest()


def _encrypt_string(value: str, user_id: str) -> str:
    """Encrypt a single string value. Returns base64 encoded string."""
    import base64
    import json
    import secrets

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _derive_key(user_id)
    nonce = secrets.token_bytes(12)
    plaintext = json.dumps({"v": value}).encode()
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + encrypted).decode('utf-8')


def _decrypt_string(encrypted: str, user_id: str) -> str:
    """Decrypt a base64 encoded encrypted string."""
    import base64
    import json

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _derive_key(user_id)
    encrypted_bytes = base64.b64decode(encrypted.encode('utf-8'))
    nonce = encrypted_bytes[:12]
    ciphertext = encrypted_bytes[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    data = json.loads(plaintext.decode())
    return data["v"]


async def _refresh_from_db(
    user_id: str,
    db: AsyncSession
) -> tuple[bool, OAuthToken | None, str]:
    """
    Load refresh token from DB and attempt async refresh.

    This uses the async provider-specific refresh path in storage/router.py
    instead of the synchronous token_manager.refresh_token_if_needed(). The
    synchronous path blocks the async event loop and causes timeouts / reconnect
    loops under uvicorn (especially on Render free-tier spin-down).
    """
    try:
        # Get session from DB (not User - sessions store the tokens)
        result = await db.execute(select(SessionModel).where(SessionModel.user_id == user_id))
        session_row = result.scalar_one_or_none()

        if not session_row:
            logger.warning(f"Session {user_id[:6]}*** not found in DB")
            return False, None, RefreshResult.USER_NOT_FOUND

        # Decrypt refresh token
        refresh_token = None
        if session_row.refresh_token_encrypted:
            try:
                refresh_token = _decrypt_string(session_row.refresh_token_encrypted, user_id)
            except Exception as e:
                logger.warning(f"Failed to decrypt refresh token for {user_id[:6]}***: {e}")

        if not refresh_token:
            logger.warning(f"No refresh token for user {user_id[:6]}***")
            return False, None, RefreshResult.NO_REFRESH_TOKEN

        # Parse provider from user_id
        provider, role, unique = parse_user_id(user_id)
        if not provider:
            logger.error(f"Could not parse provider from user_id {user_id[:6]}***")
            return False, None, RefreshResult.PROVIDER_ERROR

        # Decrypt access token
        access_token = ""
        if session_row.access_token_encrypted:
            try:
                access_token = _decrypt_string(session_row.access_token_encrypted, user_id)
            except Exception as e:
                logger.warning(f"Failed to decrypt access token for {user_id[:6]}***: {e}")

        # Normalize naive expires_at to UTC so token.is_expired() does not crash
        # comparing aware and naive datetimes (SQLite returns naive datetimes).
        expires_at = session_row.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        # Create token object from DB data
        token = OAuthToken(
            access_token=access_token,  # May be expired
            refresh_token=refresh_token,
            expires_at=expires_at,
            provider=provider,
        )

        # Store in token_manager cache so sync helpers can find a valid token
        token_manager.store_token(user_id, token)

        # If the token is still valid, no provider call needed.
        if not token.is_expired():
            logger.debug(f"Token still valid for user {user_id[:6]}***")
            return True, token, RefreshResult.SUCCESS

        # Token expired/melting - use the async provider-specific refresh.
        # Local import avoids a top-level circular import with storage/router.py,
        # which imports _encrypt_string/_decrypt_string from this module.
        try:
            from app.modules.storage.router import refresh_access_token
            new_token_data = await refresh_access_token(db, user_id, provider, refresh_token)
        except Exception as e:
            logger.error(f"Async token refresh raised for user {user_id[:6]}***: {e}", exc_info=True)
            return False, None, RefreshResult.PROVIDER_ERROR

        if not new_token_data:
            logger.warning(f"Token refresh failed for user {user_id[:6]}***")
            return False, None, RefreshResult.REFRESH_FAILED

        # refresh_access_token already persists new tokens to the DB.
        # Rebuild the in-memory OAuthToken and cache it.
        new_token = OAuthToken(
            access_token=new_token_data["access_token"],
            refresh_token=new_token_data.get("refresh_token", refresh_token),
            expires_at=new_token_data["expires_at"],
            provider=provider,
        )
        token_manager.store_token(user_id, new_token)

        logger.info(f"Silent refresh succeeded for user {user_id[:6]}***")
        return True, new_token, RefreshResult.SUCCESS

    except Exception as e:
        logger.error(f"Error during silent refresh for user {user_id[:6]}***: {e}", exc_info=True)
        return False, None, RefreshResult.PROVIDER_ERROR


async def get_valid_token_or_redirect(
    user_id: str,
    return_to: str,
    db: AsyncSession | None = None
) -> tuple[OAuthToken | None, str | None]:
    """
    Get a valid token, or return the redirect URL for full reauth.
    
    This is the main entry point for storage middleware.
    
    Returns:
        (token, redirect_url)
        - If token is valid: (token, None)
        - If reauth needed: (None, redirect_url)
    """
    is_valid, token, status = await ensure_valid_token(user_id, db)

    if is_valid:
        return token, None

    # Refresh failed - need full reauth
    from app.core.navigation import navigation

    provider, role, unique = parse_user_id(user_id)
    reconnect_stage = navigation.get_stage("reconnect")
    reconnect_path = reconnect_stage.path if reconnect_stage else "/storage/reconnect"

    # Build reconnect URL with return_to
    reconnect_url = f"{reconnect_path}?return_to={return_to}&provider={provider}"

    logger.info(f"Reauth required for user {user_id[:6]}*** (status={status}) ▸ {reconnect_path}")
    return None, reconnect_url


def register_provider_refresh_callbacks():
    """Register all provider-specific refresh callbacks."""
    from app.core.oauth_token_manager import (
        register_dropbox_refresh_callback,
        register_google_refresh_callback,
        register_onedrive_refresh_callback,
    )

    register_google_refresh_callback()
    register_dropbox_refresh_callback()
    register_onedrive_refresh_callback()

    logger.info("All provider refresh callbacks registered")


# Auto-register on module import
register_provider_refresh_callbacks()
