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
) -> str:
    """
    Create a CSRF-safe OAuth state token and persist it.

    Returns the state string to include in the OAuth redirect URL.
    """
    state = secrets.token_urlsafe(32)
    now = utc_now()
    oauth_state = OAuthState(
        id=state,
        provider=provider,
        role=role,
        created_at=now,
        expires_at=now + timedelta(minutes=15),
    )
    db.add(oauth_state)
    await db.commit()
    return state


async def consume_oauth_state(db: AsyncSession, state: str) -> dict:
    """
    Validate and consume an OAuth state token. Returns the state data.
    Raises HTTPException if state is invalid or expired.
    """
    result = await db.execute(select(OAuthState).where(OAuthState.id == state))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    data = {
        "provider": row.provider,
        "role": getattr(row, "role", "tenant") or "tenant",
        "callback_url": getattr(row, "callback_url", None),
    }

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
    settings = get_settings()
    oauth_config = config.get_oauth_config(provider)

    if provider == "google_drive":
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
        params = {
            "client_id": settings.dropbox_app_key,
            "redirect_uri": callback_url,
            "response_type": "code",
            "state": state,
            "token_access_type": "offline",
        }
    elif provider == "onedrive":
        params = {
            "client_id": settings.onedrive_client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": " ".join(oauth_config["scopes"]),
            "state": state,
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

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
        raise HTTPException(status_code=400, detail=f"No token URL for provider: {provider}")

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
            raise HTTPException(status_code=400, detail="Provider not implemented")

    if response.status_code != 200:
        provider_error = "token_exchange_failed"
        try:
            payload = response.json()
            provider_error = payload.get("error_description") or payload.get("error") or provider_error
        except Exception:
            if response.text:
                provider_error = response.text[:200]

        raise HTTPException(
            status_code=400,
            detail={"error": "token_exchange_failed", "message": f"Token exchange failed: {provider_error}"},
        )

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
        raise HTTPException(status_code=400, detail="Identity endpoint unavailable")

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
            raise HTTPException(status_code=401, detail="OAuth identity verification failed")

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
            raise HTTPException(status_code=401, detail="Provider did not return a subject ID")

        return {"provider_subject": subject, "email": email, "display_name": name}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Unable to verify storage account identity")


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

    if existing:
        logger.info("Matched existing user %s by provider subject", existing.id[:6] + "***")
        return existing.id, False

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
    from app.routers.storage import save_session_to_db

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

    # 6b. Create vault folders + system files + verification
    from app.modules.onboarding.vault import init_vault
    # Extract base_url from callback_url (e.g. "https://semptify.com/onboarding/callback/google_drive")
    _base_url = callback_url.split(config.route_prefix)[0] if config.route_prefix in callback_url else ""
    try:
        vault_result = await init_vault(
            db=db,
            user_id=user_id,
            provider_name=provider,
            access_token=access_token,
            config=config,
            base_url=_base_url,
        )
        logger.info("init_vault result for user %s: %s", user_id[:6] + "***", vault_result)
    except Exception as vault_exc:
        logger.error("init_vault crashed for user %s: %s", user_id[:6] + "***", vault_exc, exc_info=True)
        vault_result = {"ok": False, "message": str(vault_exc)}
    if not vault_result["ok"]:
        logger.warning("Vault creation failed during callback: %s", vault_result["message"])

    # 7. Determine routing
    from app.modules.onboarding.gates import check_gate
    vault_initialized = await check_gate(db, user_id, "vault_initialized")

    logger.info(
        "Onboarding callback complete: user=%s new=%s vault_initialized=%s",
        user_id[:6] + "***", is_new, vault_initialized,
    )

    return {
        "user_id": user_id,
        "is_new": is_new,
        "vault_initialized": vault_initialized,
    }
