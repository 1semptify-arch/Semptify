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
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.oauth_token_manager import token_manager, OAuthToken
from app.core.user_id import parse_user_id, verify_user_id, COOKIE_USER_ID
from app.core.database import get_session_factory
from app.models.models import User

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
    db: Optional[AsyncSession] = None
) -> Tuple[bool, Optional[OAuthToken], str]:
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


async def _refresh_from_db(
    user_id: str,
    db: AsyncSession
) -> Tuple[bool, Optional[OAuthToken], str]:
    """
    Load refresh token from DB and attempt refresh.
    """
    try:
        # Get user from DB
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User {user_id[:6]}*** not found in DB")
            return False, None, RefreshResult.USER_NOT_FOUND
        
        if not user.refresh_token:
            logger.warning(f"No refresh token for user {user_id[:6]}***")
            return False, None, RefreshResult.NO_REFRESH_TOKEN
        
        # Parse provider from user_id
        provider, role, unique = parse_user_id(user_id)
        if not provider:
            logger.error(f"Could not parse provider from user_id {user_id[:6]}***")
            return False, None, RefreshResult.PROVIDER_ERROR
        
        # Create token object from DB data
        token = OAuthToken(
            access_token=user.access_token or "",  # May be expired
            refresh_token=user.refresh_token,
            expires_at=user.token_expires_at,
            provider=provider,
        )
        
        # Attempt refresh
        new_token = token_manager.refresh_token_if_needed(user_id)
        
        if new_token and not new_token.is_expired():
            # Update DB with new access token
            user.access_token = new_token.access_token
            user.token_expires_at = new_token.expires_at
            if new_token.refresh_token != user.refresh_token:
                user.refresh_token = new_token.refresh_token
            await db.commit()
            
            logger.info(f"Silent refresh succeeded for user {user_id[:6]}***")
            return True, new_token, RefreshResult.SUCCESS
        else:
            logger.warning(f"Token refresh failed for user {user_id[:6]}***")
            return False, None, RefreshResult.REFRESH_FAILED
            
    except Exception as e:
        logger.error(f"Error during silent refresh for user {user_id[:6]}***: {e}", exc_info=True)
        return False, None, RefreshResult.PROVIDER_ERROR


async def get_valid_token_or_redirect(
    user_id: str,
    return_to: str,
    db: Optional[AsyncSession] = None
) -> Tuple[Optional[OAuthToken], Optional[str]]:
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
    from app.core.ssot_guard import ssot_redirect
    
    provider, role, unique = parse_user_id(user_id)
    reconnect_stage = navigation.get_stage("reconnect")
    reconnect_path = reconnect_stage.path if reconnect_stage else "/storage/reconnect"
    
    # Build reconnect URL with return_to
    reconnect_url = f"{reconnect_path}?return_to={return_to}&provider={provider}"
    
    logger.info(f"Reauth required for user {user_id[:6]}*** (status={status}) → {reconnect_path}")
    return None, reconnect_url


def register_provider_refresh_callbacks():
    """Register all provider-specific refresh callbacks."""
    from app.core.oauth_token_manager import (
        register_google_refresh_callback,
        register_dropbox_refresh_callback,
        register_onedrive_refresh_callback
    )
    
    register_google_refresh_callback()
    register_dropbox_refresh_callback()
    register_onedrive_refresh_callback()
    
    logger.info("All provider refresh callbacks registered")


# Auto-register on module import
register_provider_refresh_callbacks()
