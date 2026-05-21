"""
OAuth flow for onboarding — token exchange, identity verification, user creation.

This module handles the ONBOARDING OAuth path only. It creates new users,
stores sessions, caches tokens, and marks the storage_connected gate.
Reconnect (returning users refreshing tokens) is NOT handled here.
"""

import logging
import secrets
from datetime import timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.utc import utc_now
from app.core.user_id import generate_user_id
from app.core.cookie_auth import set_auth_cookie
from app.core.oauth_token_manager import token_manager, OAuthToken
from app.models.models import User, OAuthState

from app.modules.onboarding.config import OnboardingConfig
from app.modules.onboarding.gates import mark_gate

logger = logging.getLogger(__name__)

ALLOWED_ROLES = {"tenant", "advocate", "legal", "admin", "manager", "user"}


# ============================================================================
# OAuth State Management
# ============================================================================

async def create_oauth_state(
    db: AsyncSession,
    provider: str,
    role: str,
    callback_url: str,
    force_fresh: bool = False,
) -> str:
    """
    Create a CSRF-safe OAuth state token and persist it.

    Returns the state string to include in the OAuth redirect URL.
    """
    state = secrets.token_urlsafe(32)
    now = utc_now()
    # Create OAuthState with force_fresh if field exists (migration might not have run yet)
    oauth_state_dict = {
        "id": state,
        "provider": provider,
        "role": role,
        "created_at": now,
        "expires_at": now + timedelta(minutes=15),
    }
    
    # Only add force_fresh if the field exists in the model
    try:
        oauth_state_dict["force_fresh"] = force_fresh
        oauth_state = OAuthState(**oauth_state_dict)
    except Exception:
        # Migration hasn't run yet, create without force_fresh field
        oauth_state = OAuthState(**{k: v for k, v in oauth_state_dict.items() if k != "force_fresh"})
    db.add(oauth_state)
    await db.commit()
    return state


async def consume_oauth_state(db: AsyncSession, state: str) -> dict:
    """
    Validate and consume an OAuth state token. Returns the state data.
    Raises ValueError if state is invalid or expired.
    """
    result = await db.execute(select(OAuthState).where(OAuthState.id == state))
    row = result.scalar_one_or_none()
    if not row:
        logger.error("consume_oauth_state: state not found in DB: %s", state[:12] + "***")
        raise ValueError("Invalid or expired OAuth state — token not found")

    # Check expiry
    now = utc_now()
    if row.expires_at and row.expires_at < now:
        logger.error("consume_oauth_state: state expired at %s (now=%s)", row.expires_at, now)
        await db.delete(row)
        await db.commit()
        raise ValueError("OAuth state token expired — please start the OAuth flow again")

    data = {
        "provider": row.provider,
        "role": getattr(row, "role", "tenant") or "tenant",
        "callback_url": getattr(row, "callback_url", None),
        "force_fresh": getattr(row, "force_fresh", False),
    }

    logger.info("consume_oauth_state: valid state consumed for provider=%s role=%s", data["provider"], data["role"])

    # Consume (delete) the state — single use
    await db.delete(row)
    await db.commit()
    return data


# ============================================================================
# OAuth Initiation
# ============================================================================

def build_oauth_url(config: OnboardingConfig, provider: str, state: str, callback_url: str) -> str:
    """
    Build the provider-specific OAuth authorization URL.
    """
    logger.info("build_oauth_url: provider=%s state=%s callback=%s", provider, state[:12] + "***", callback_url)
    
    try:
        settings = get_settings()
        logger.info("build_oauth_url: settings loaded successfully")
    except Exception as e:
        logger.error("build_oauth_url: failed to load settings: %s", e)
        raise
    
    try:
        oauth_config = config.get_oauth_config(provider)
        logger.info("build_oauth_url: oauth_config loaded for provider=%s", provider)
    except Exception as e:
        logger.error("build_oauth_url: failed to get oauth_config: %s", e)
        raise

    if provider == "google_drive":
        if not settings.google_drive_client_id:
            raise ValueError("Google Drive client ID not configured")
        params = {
            "client_id": settings.google_drive_client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": " ".join(oauth_config["scopes"]),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
    elif provider == "dropbox":
        if not settings.dropbox_app_key:
            raise ValueError("Dropbox app key not configured")
        params = {
            "client_id": settings.dropbox_app_key,
            "redirect_uri": callback_url,
            "response_type": "code",
            "state": state,
            "token_access_type": "offline",
        }
    elif provider == "onedrive":
        if not settings.onedrive_client_id:
            raise ValueError("OneDrive client ID not configured")
        params = {
            "client_id": settings.onedrive_client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": " ".join(oauth_config["scopes"]),
            "state": state,
        }
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    return f"{oauth_config['auth_url']}?{urlencode(params)}"


# ============================================================================
# Token Exchange
# ============================================================================

async def exchange_code_for_tokens(
    provider: str,
    code: str,
    redirect_uri: str,
) -> dict:
    """
    Exchange an OAuth authorization code for access/refresh tokens.
    Returns the raw token response dict.
    """
    settings = get_settings()

    TOKEN_URLS = {
        "google_drive": "https://oauth2.googleapis.com/token",
        "dropbox": "https://api.dropboxapi.com/oauth2/token",
        "onedrive": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    }
    token_url = TOKEN_URLS.get(provider)
    if not token_url:
        raise ValueError(f"No token URL for provider: {provider}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        if provider == "google_drive":
            response = await client.post(token_url, data={
                "code": code,
                "client_id": settings.google_drive_client_id,
                "client_secret": settings.google_drive_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
        elif provider == "dropbox":
            response = await client.post(token_url, data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }, auth=(settings.dropbox_app_key, settings.dropbox_app_secret))
        elif provider == "onedrive":
            response = await client.post(token_url, data={
                "code": code,
                "client_id": settings.onedrive_client_id,
                "client_secret": settings.onedrive_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
        else:
            raise ValueError(f"Provider not implemented: {provider}")

    if response.status_code != 200:
        provider_error = "token_exchange_failed"
        try:
            payload = response.json()
            provider_error = payload.get("error_description") or payload.get("error") or provider_error
        except Exception:
            if response.text:
                provider_error = response.text[:200]

        logger.error("Token exchange failed: provider=%s status=%s error=%s", provider, response.status_code, provider_error)
        raise RuntimeError(f"Token exchange failed ({provider}): {provider_error}")

    return response.json()


# ============================================================================
# Identity Verification
# ============================================================================

async def fetch_provider_identity(provider: str, access_token: str) -> dict:
    """
    Fetch provider-asserted account identity (subject ID, email, display name).

    Returns dict with keys: provider_subject, email, display_name.
    """
    USERINFO_URLS = {
        "google_drive": "https://www.googleapis.com/oauth2/v2/userinfo",
        "dropbox": "https://api.dropboxapi.com/2/users/get_current_account",
        "onedrive": "https://graph.microsoft.com/v1.0/me",
    }
    url = USERINFO_URLS.get(provider)
    if not url:
        raise ValueError(f"Identity endpoint unavailable for provider: {provider}")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if provider == "dropbox":
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                    content="null",
                )
            else:
                response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})

        if response.status_code != 200:
            logger.error("Identity verification failed: provider=%s status=%s body=%s", provider, response.status_code, response.text[:200])
            raise RuntimeError(f"OAuth identity verification failed ({provider}): HTTP {response.status_code}")

        payload = response.json()

        if provider == "google_drive":
            subject = payload.get("id")
            email = payload.get("email")
            name = payload.get("name")
        elif provider == "dropbox":
            subject = payload.get("account_id")
            email = payload.get("email")
            name_obj = payload.get("name") if isinstance(payload.get("name"), dict) else {}
            name = name_obj.get("display_name") or payload.get("display_name")
        elif provider == "onedrive":
            subject = payload.get("id")
            email = payload.get("mail") or payload.get("userPrincipalName")
            name = payload.get("displayName")
        else:
            subject, email, name = None, None, None

        if not subject:
            raise RuntimeError(f"Provider did not return a subject ID for: {provider}")

        return {"provider_subject": subject, "email": email, "display_name": name}

    except (RuntimeError, ValueError):
        raise
    except Exception as e:
        logger.error("Identity verification exception: provider=%s error=%s", provider, str(e), exc_info=True)
        raise RuntimeError(f"Unable to verify storage account identity ({provider}): {e}") from e


# ============================================================================
# User Matching / Creation
# ============================================================================

async def find_or_create_user(
    db: AsyncSession,
    provider: str,
    provider_subject: str,
    role: str,
) -> tuple:
    """
    Find existing user by provider subject, or create a new one.

    Returns (user_id: str, is_new: bool).
    """
    result = await db.execute(
        select(User).where(
            User.primary_provider == provider,
            User.storage_user_id == provider_subject,
        )
    )
    existing = result.scalar_one_or_none()

    # Check for fresh session parameter to bypass existing user lookup
    # Handle missing force_fresh field gracefully until migration runs
    force_fresh = state_data.get("force_fresh", False)
    
    if existing and not force_fresh:
        logger.info("Matched existing user %s by provider subject", existing.id[:6] + "***")
        return existing.id, False
    
    if existing and force_fresh:
        logger.info("Force fresh: bypassing existing user %s for new ID generation", existing.id[:6] + "***")

    # New user
    if role not in ALLOWED_ROLES:
        role = "tenant"
    user_id = generate_user_id(provider, role)

    # Create User row
    # Strip HMAC signature for database storage (User.id is VARCHAR(24))
    db_user_id = user_id.split('.')[0] if '.' in user_id else user_id
    new_user = User(
        id=db_user_id,
        primary_provider=provider,
        storage_user_id=provider_subject,
    )
    db.add(new_user)
    await db.commit()

    logger.info("Created new user %s (provider=%s, role=%s)", db_user_id[:6] + "***", provider, role)
    return db_user_id, True


# ============================================================================
# Session Persistence
# ============================================================================

async def save_session(
    db: AsyncSession,
    user_id: str,
    provider: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
) -> None:
    """
    Save OAuth session to DB and cache token in memory.
    """
    from app.modules.storage.router import save_session_to_db

    expires_at = utc_now() + timedelta(seconds=expires_in)

    # Persist to database
    await save_session_to_db(
        db=db,
        user_id=user_id,
        provider=provider,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )

    # Cache in-memory so vault_init (called seconds later) can find it
    token_manager.store_token(user_id, OAuthToken(
        access_token=access_token,
        refresh_token=refresh_token or None,
        expires_at=expires_at,
        provider=provider,
    ))

    logger.info("Session saved for user %s (provider=%s)", user_id[:6] + "***", provider)


# ============================================================================
# Complete Onboarding Callback Handler
# ============================================================================

async def handle_onboarding_callback(
    db: AsyncSession,
    provider: str,
    code: str,
    state: str,
    callback_url: str,
    config: OnboardingConfig,
) -> dict:
    """
    Complete the onboarding OAuth callback. This is the single function that
    the router calls. It handles everything:

    1. Validate state token
    2. Exchange code for tokens
    3. Fetch provider identity
    4. Find or create user
    5. Save session + cache token
    6. Mark storage_connected gate
    7. Return routing info

    Returns dict with: user_id, is_new, vault_initialized, landing.
    """
    # 1. Validate state
    state_data = await consume_oauth_state(db, state)
    role = state_data.get("role", "tenant")

    # 2. Exchange code for tokens
    token_data = await exchange_code_for_tokens(provider, code, callback_url)
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)

    # 3. Fetch identity
    identity = await fetch_provider_identity(provider, access_token)
    provider_subject = identity["provider_subject"]

    # 4. Find or create user
    user_id, is_new = await find_or_create_user(db, provider, provider_subject, role)

    # 5. Save session + cache token
    await save_session(db, user_id, provider, access_token, refresh_token, expires_in)

    # 6. Mark storage_connected gate
    await mark_gate(db, user_id, "storage_connected")

    # Vault installation now happens on vault-setup page (async, with loading screen)
    # Do NOT install here — it blocks the HTTP response and creates poor UX

    # 7. Determine routing — always route to vault-setup page for first-time setup
    # This shows loading screen with "Did you know" facts during folder creation
    logger.info(
        "Onboarding callback complete: user=%s new=%s → vault-setup page",
        user_id[:6] + "***", is_new,
    )

    return {
        "user_id": user_id,
        "is_new": is_new,
        "vault_initialized": False,  # Force vault-setup page for first-time users
    }
