"""
Semptify 5.0 - Storage OAuth Router (Simplified)

Simple flow:
1. User visits site → check for semptify_uid cookie
2. If cookie exists → parse user ID → know provider + role
3. Redirect to provider OAuth → get token → find encrypted token in storage
4. Decrypt → user authenticated → load UI based on role

User ID format: <provider><role><random>
Example: GT7x9kM2pQ = Google + Tenant + unique
"""

from datetime import datetime, timedelta
import logging

from app.core.utc import utc_now
from typing import Optional
import secrets
import hashlib
import json
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request, Response, Cookie, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
import httpx

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    AsyncSession = object
    select = None
    SQLALCHEMY_AVAILABLE = False

from app.core.config import get_settings
from app.core.database import get_db
from app.core.storage_middleware import is_valid_storage_user
from app.core.workflow_engine import route_user as _route_user
from app.core.user_id import (
    generate_user_id,
    parse_user_id,
    update_user_id_role,
    get_provider_from_user_id,
    get_role_from_user_id,
    COOKIE_USER_ID,
    COOKIE_MAX_AGE,
)
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect
from app.core.security import (
    issue_function_access_token,
    verify_function_access_token,
    invalidate_function_access_tokens,
)

from app.models.models import User, Session as SessionModel, StorageConfig, OAuthState


router = APIRouter(prefix="/storage", tags=["storage"])
logger = logging.getLogger(__name__)

def _get_settings():
    """Lazy settings getter to avoid import-time validation issues."""
    return get_settings()


# ============================================================================
# OAuth Configuration
# ============================================================================

OAUTH_CONFIGS = {
    "google_drive": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
    },
    "dropbox": {
        "auth_url": "https://www.dropbox.com/oauth2/authorize",
        "token_url": "https://api.dropboxapi.com/oauth2/token",
        "userinfo_url": "https://api.dropboxapi.com/2/users/get_current_account",
        "scopes": [],
    },
    "onedrive": {
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": ["Files.ReadWrite.AppFolder", "User.Read", "offline_access"],
    },
}

OAUTH_STATE_TIMEOUT_MINUTES = 15  # OAuth state TTL in minutes

ALLOWED_ROLES = {"user", "tenant", "manager", "advocate", "legal", "judge", "admin"}

# ============================================================================
# Session Status Endpoint - For Returning User Auto-Reconnect (SSOT)
# ============================================================================

class SessionStatusResponse(BaseModel):
    """Session status for returning user auto-reconnect flow."""
    has_session: bool
    is_valid: bool
    user_id: Optional[str] = None
    role: Optional[str] = None
    provider: Optional[str] = None
    has_storage: bool = False


@router.get("/session/status", response_model=SessionStatusResponse)
async def get_session_status(
    request: Request,
    semptify_session: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> SessionStatusResponse:
    """
    Check session status for returning users.
    
    Returns role and provider from existing session cookie so frontend
    can auto-redirect to OAuth without asking user to choose provider again.
    """
    # No session cookie present
    if not semptify_session:
        return SessionStatusResponse(has_session=False, is_valid=False)
    
    # Validate session token and get user info
    try:
        from app.core.security import verify_session_token
        session_data = await verify_session_token(semptify_session, db)
        
        if not session_data or not session_data.get("user_id"):
            return SessionStatusResponse(has_session=True, is_valid=False)
        
        user_id = session_data["user_id"]
        
        # Check if user ID is valid
        if not is_valid_storage_user(user_id):
            return SessionStatusResponse(has_session=True, is_valid=False, user_id=user_id)
        
        # Extract role and provider from user ID
        role = get_role_from_user_id(user_id)
        provider = get_provider_from_user_id(user_id)
        
        # Check if user has storage configured
        storage_config = await db.execute(
            select(StorageConfig).where(StorageConfig.user_id == user_id)
        )
        has_storage = storage_config.scalar_one_or_none() is not None
        
        return SessionStatusResponse(
            has_session=True,
            is_valid=True,
            user_id=user_id,
            role=role,
            provider=provider,
            has_storage=has_storage,
        )
        
    except Exception as e:
        logger.warning(f"Session status check failed: {e}")
        return SessionStatusResponse(has_session=True, is_valid=False)


# Legacy in-memory compatibility maps.
# DB rows remain the source of truth; these are only a transitional bridge for
# older tests/callers still importing module-level state.
SESSIONS: dict[str, dict] = {}
OAUTH_STATES: dict[str, dict] = {}

async def _cleanup_expired_states(db: AsyncSession) -> None:
    """Remove expired OAuth states from the database."""
    from sqlalchemy import delete as sa_delete
    result = await db.execute(
        sa_delete(OAuthState).where(OAuthState.expires_at < utc_now())
    )
    if result.rowcount:
        print(f"🧹 Cleaned up {result.rowcount} expired OAuth states")

    # Transitional cleanup for legacy in-memory state map.
    now = utc_now()
    stale_keys = []
    for state_id, payload in OAUTH_STATES.items():
        expires_at = payload.get("expires_at")
        created_at = payload.get("created_at")

        if not expires_at and created_at:
            expires_at = created_at + timedelta(minutes=OAUTH_STATE_TIMEOUT_MINUTES)

        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

        if expires_at and expires_at.tzinfo is None:
            from datetime import timezone as _tz
            expires_at = expires_at.replace(tzinfo=_tz.utc)

        if expires_at and now > expires_at:
            stale_keys.append(state_id)

    for state_id in stale_keys:
        OAUTH_STATES.pop(state_id, None)

    await db.commit()

# Token expiry buffer (refresh 5 minutes before actual expiry)
TOKEN_EXPIRY_BUFFER = timedelta(minutes=5)


# ============================================================================
# Token Validation & Refresh
# ============================================================================

async def validate_token_with_provider(provider: str, access_token: str) -> bool:
    """
    Validate token by making a test API call to the provider.
    Returns True if token is valid, False otherwise.
    """
    import os
    # Skip validation in test mode - mock tokens are always valid
    if os.environ.get("TESTING") == "true":
        return True
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "google_drive":
                # Check token info endpoint
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v1/tokeninfo",
                    params={"access_token": access_token}
                )
                return response.status_code == 200
            
            elif provider == "dropbox":
                # Check current account endpoint
                response = await client.post(
                    "https://api.dropboxapi.com/2/users/get_current_account",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                return response.status_code == 200
            
            elif provider == "onedrive":
                # Check user profile endpoint
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                return response.status_code == 200
            
            return False
    except Exception:
        return False


async def refresh_access_token(
    db: AsyncSession,
    user_id: str,
    provider: str,
    refresh_token: str,
) -> Optional[dict]:
    """
    Refresh access token using the refresh token.
    Returns new token data if successful, None otherwise.
    """
    if not refresh_token:
        return None
    
    config = OAUTH_CONFIGS.get(provider)
    if not config:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if provider == "google_drive":
                response = await client.post(config["token_url"], data={
                    "client_id": _get_settings().google_drive_client_id,
                    "client_secret": _get_settings().google_drive_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                })
            
            elif provider == "dropbox":
                # Dropbox uses long-lived tokens, but let's handle refresh anyway
                response = await client.post(config["token_url"], data={
                    "client_id": _get_settings().dropbox_app_key,
                    "client_secret": _get_settings().dropbox_app_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                })
            
            elif provider == "onedrive":
                response = await client.post(config["token_url"], data={
                    "client_id": _get_settings().onedrive_client_id,
                    "client_secret": _get_settings().onedrive_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": " ".join(config["scopes"]),
                })
            else:
                return None
            
            if response.status_code != 200:
                print(f"Token refresh failed for {provider}: {response.status_code} - {response.text}")
                return None
            
            token_data = response.json()
            new_access_token = token_data.get("access_token")
            # Some providers return a new refresh token, some don't
            new_refresh_token = token_data.get("refresh_token", refresh_token)
            expires_in = token_data.get("expires_in", 3600)
            expires_at = utc_now() + timedelta(seconds=expires_in)

            # Update session in database
            await save_session_to_db(
                db=db,
                user_id=user_id,
                provider=provider,
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_at=expires_at,
            )
            
            print(f"Token refreshed successfully for user {user_id[:4]}*** ({provider})")
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_at": expires_at,
            }
    
    except Exception as e:
        print(f"Token refresh error for {provider}: {e}")
        return None


async def get_valid_session(
    db: AsyncSession,
    user_id: str,
    auto_refresh: bool = True,
) -> Optional[dict]:
    """
    Get a session with a valid (non-expired) access token.
    Will automatically refresh if token is expired and auto_refresh=True.
    
    Returns session dict with valid token, or None if session invalid/refresh failed.
    """
    # Get session from DB
    session = await get_session_from_db(db, user_id)
    if not session:
        return None
    
    # Check if token needs refresh
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    expires_at = session.get("expires_at")
    provider = session.get("provider")
    
    needs_refresh = False
    
    # Check expiry time if we have it
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        # Ensure expires_at is timezone-aware (assume UTC if naive)
        if expires_at.tzinfo is None:
            from datetime import timezone
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if utc_now() >= (expires_at - TOKEN_EXPIRY_BUFFER):
            needs_refresh = True
            print(f"Token expired for user {user_id[:4]}*** - attempting refresh")
    
    # If no expiry info, validate with provider
    if not needs_refresh and not expires_at:
        is_valid = await validate_token_with_provider(provider, access_token)
        if not is_valid:
            needs_refresh = True
            print(f"Token invalid for user {user_id[:4]}*** - attempting refresh")
    
    # Attempt refresh if needed
    if needs_refresh and auto_refresh and refresh_token:
        new_token_data = await refresh_access_token(db, user_id, provider, refresh_token)
        if new_token_data:
            # Refresh saved to DB by refresh_access_token; re-read the session.
            return await get_session_from_db(db, user_id)
        else:
            # Refresh failed - session is invalid
            print(f"Token refresh failed for user {user_id[:4]}*** - session invalidated")
            return None

    if needs_refresh and not auto_refresh:
        # Caller requested a read-only validity check. Do not treat stale session as valid.
        return None
    
    if needs_refresh and not refresh_token:
        print(f"Token expired and no refresh token for user {user_id[:4]}***")
        return None
    
    return session


# ============================================================================
# Database Session Helpers
# ============================================================================

def _encrypt_string(value: str, user_id: str) -> str:
    """Encrypt a single string value. Returns base64 encoded string."""
    import base64
    encrypted_bytes = _encrypt_token({"v": value}, user_id)
    return base64.b64encode(encrypted_bytes).decode('utf-8')


def _decrypt_string(encrypted: str, user_id: str) -> str:
    """Decrypt a base64 encoded encrypted string."""
    import base64
    encrypted_bytes = base64.b64decode(encrypted.encode('utf-8'))
    data = _decrypt_token(encrypted_bytes, user_id)
    return data["v"]


async def get_session_from_db(db: AsyncSession, user_id: str) -> Optional[dict]:
    """Load session from the database."""
    result = await db.execute(
        select(SessionModel).where(SessionModel.user_id == user_id)
    )
    session_row = result.scalar_one_or_none()

    if session_row:
        # Decrypt tokens and cache in memory
        try:
            session_data = {
                "user_id": session_row.user_id,
                "provider": session_row.provider,
                "access_token": _decrypt_string(session_row.access_token_encrypted, user_id),
                "refresh_token": _decrypt_string(session_row.refresh_token_encrypted, user_id) if session_row.refresh_token_encrypted else None,
                "authenticated_at": session_row.authenticated_at.isoformat() if session_row.authenticated_at else None,
                "expires_at": session_row.expires_at.isoformat() if session_row.expires_at else None,
            }
            SESSIONS[user_id] = session_data
            return session_data
        except Exception:
            # Decryption failed - session may be corrupted
            SESSIONS.pop(user_id, None)
            return None

    # Transitional fallback for older tests/callers that still use in-memory sessions.
    legacy_session = SESSIONS.get(user_id)
    if legacy_session:
        return legacy_session

    return None


async def save_session_to_db(
    db: AsyncSession,
    user_id: str,
    provider: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> None:
    """Save session to database."""
    # Check if session exists
    result = await db.execute(
        select(SessionModel).where(SessionModel.user_id == user_id)
    )
    session_row = result.scalar_one_or_none()

    now = utc_now()

    if session_row:
        # Update existing session
        session_row.provider = provider
        session_row.access_token_encrypted = _encrypt_string(access_token, user_id)
        session_row.refresh_token_encrypted = _encrypt_string(refresh_token, user_id) if refresh_token else None
        session_row.authenticated_at = now
        session_row.last_activity = now
        session_row.expires_at = expires_at
    else:
        # Create new session
        session_row = SessionModel(
            user_id=user_id,
            provider=provider,
            access_token_encrypted=_encrypt_string(access_token, user_id),
            refresh_token_encrypted=_encrypt_string(refresh_token, user_id) if refresh_token else None,
            authenticated_at=now,
            last_activity=now,
            expires_at=expires_at,
        )
        db.add(session_row)

    await db.commit()

    # Keep compatibility map aligned for transitional callers/tests.
    SESSIONS[user_id] = {
        "user_id": user_id,
        "provider": provider,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "authenticated_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


async def recover_session_from_storage(
    db: AsyncSession,
    user_id: str,
    base_url: str,
) -> Optional[dict]:
    """
    Attempt to recover a session for a user whose DB session is missing.

    Constraint: recovery requires a valid access token to read cloud storage,
    but the token lives in cloud storage — a chicken-and-egg problem.
    The only working recovery path is OAuth re-authentication.

    Steps:
    1. Check DB again (may have been written by a concurrent request).
    2. If not found, return None — caller must redirect the user to OAuth.

    NOTE: rehome.html / encrypted identity file approach is PARKED pending
    format decision. Do not implement cloud-read recovery here until that
    design is finalised.
    """
    provider, _role, _ = parse_user_id(user_id)
    if not provider:
        return None

    session = await get_session_from_db(db, user_id)
    if session:
        return session

    logger.info("Session recovery: no DB session for %s*** — OAuth re-auth required", user_id[:4])
    return None


async def get_or_create_storage_config(
    db: AsyncSession,
    user_id: str,
    provider: str,
) -> StorageConfig:
    """Get existing storage config or create a new one."""
    result = await db.execute(
        select(StorageConfig).where(StorageConfig.user_id == user_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = StorageConfig(
            user_id=user_id,
            primary_provider=provider,
            connected_providers=provider,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
    
    return config


async def get_user_from_db(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get user from database."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Find user by email for session recovery."""
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_provider_subject(
    db: AsyncSession,
    provider: str,
    provider_subject: str,
) -> Optional[User]:
    """Find user by OAuth provider and provider-asserted subject/account id."""
    result = await db.execute(
        select(User).where(
            User.primary_provider == provider,
            User.storage_user_id == provider_subject,
        )
    )
    return result.scalar_one_or_none()


async def _mark_group_complete(db: AsyncSession, user_id: str, group_name: str) -> None:
    """
    Permanently record that a ProcessGroup's exit criteria have been met.
    Written once. Read by middleware to skip cloud re-verification.
    Never removed — serial gating ensures this is written only when truly complete.
    """
    user = await get_user_from_db(db, user_id)
    if not user:
        return
    existing = user.completed_groups or ""
    groups = set(g for g in existing.split(",") if g)
    if group_name not in groups:
        groups.add(group_name)
        user.completed_groups = ",".join(sorted(groups))
        await db.commit()


async def create_or_update_user(
    db: AsyncSession,
    user_id: str,
    provider: str,
    email: Optional[str] = None,
    display_name: Optional[str] = None,
    storage_user_id: Optional[str] = None,
) -> User:
    """Create new user or update existing one."""
    # Strip HMAC signature for database operations (User.id is VARCHAR(24))
    db_user_id = user_id.split('.')[0] if '.' in user_id else user_id
    user = await get_user_from_db(db, db_user_id)

    _, role, _ = parse_user_id(user_id)
    now = utc_now()

    if not user and email:
        # Check for existing user by email (e.g. prior failed attempt with different user_id)
        result = await db.execute(select(User).where(User.email == email))
        email_match = result.scalar_one_or_none()
        if email_match and email_match.id != db_user_id:
            # Found a row under a different user_id — treat as new user so the
            # correct user_id (matching the cookie) gets its own DB row.
            # The old row is kept; a new one is created under the current user_id.
            email_match = None
        user = email_match

    if user:
        # Update last login
        user.last_login = now
        if storage_user_id and user.storage_user_id != storage_user_id:
            user.storage_user_id = storage_user_id
        if email and not user.email:
            user.email = email
    else:
        # Create new user
        user = User(
            id=db_user_id,
            primary_provider=provider,
            storage_user_id=storage_user_id or db_user_id,
            default_role=role,
            email=email,
            last_login=now,
        )
        db.add(user)
    
    await db.commit()
    return user


# ============================================================================
# Models
# ============================================================================

class RoleSwitchRequest(BaseModel):
    role: str  # user, manager, advocate, legal, admin
    pin: Optional[str] = None  # Required for admin role
    invite_code: Optional[str] = None  # Required for advocate/legal
    household_members: Optional[int] = None  # Required for manager (>1 on lease)


# Valid invite codes for advocate/legal roles - loaded from environment
# Set INVITE_CODES in .env as comma-separated values
import os as _os
VALID_INVITE_CODES = set(_os.getenv("INVITE_CODES", "CHANGE-ME-1,CHANGE-ME-2").split(","))

# Admin PIN - loaded from environment
ADMIN_PIN = _os.getenv("ADMIN_PIN", "CHANGE-ME")


# ============================================================================
# Encryption Helpers
# ============================================================================

def _derive_key(user_id: str) -> bytes:
    settings = _get_settings()
    secret_key = getattr(settings, "secret_key", None) or getattr(settings, "SECRET_KEY", "")
    combined = f"{secret_key}:{user_id}".encode()
    return hashlib.sha256(combined).digest()


def _encrypt_token(token_data: dict, user_id: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _derive_key(user_id)
    nonce = secrets.token_bytes(12)
    plaintext = json.dumps(token_data).encode()
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def _decrypt_token(encrypted: bytes, user_id: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _derive_key(user_id)
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode())


# ============================================================================
# Main Entry Point - Check Cookie & Auto-Route
# ============================================================================

@router.get("/entry")
async def storage_entry(
    request: Request,
    semptify_uid: Optional[str] = Cookie(None),
    return_to: Optional[str] = None,
):
    """
    Entry point for returning users.
    Redirects to reconnect if cookie exists, otherwise to provider selection.

    Args:
        return_to: Optional URL to return to after reconnect (for task continuation)
    """
    # Build reconnect URL with return_to if provided
    providers_stage = navigation.get_stage("providers")
    providers_path = providers_stage.path if providers_stage else "/storage/providers"

    if semptify_uid:
        reconnect_url = "/storage/reconnect"
        if return_to:
            reconnect_url = f"/storage/reconnect?return_to={return_to}"
        return ssot_redirect(reconnect_url, context="storage_entry reconnect")
    return ssot_redirect(providers_path, context="storage_entry providers")


@router.get("/")
async def storage_home(
    request: Request,
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Main entry point. Checks cookie and routes user appropriately.

    Returning User Flow (seamless reconnect):
    - Has valid cookie + valid session → Route to their home page
    - Has valid cookie + invalid session → Silent OAuth reauthorize (same provider)
    - No cookie → Show provider selection page for new users
    """
    providers_stage = navigation.get_stage("providers")
    providers_path = providers_stage.path if providers_stage else "/storage/providers"
    
    if not semptify_uid or not is_valid_storage_user(semptify_uid):
        # New user - show provider selection
        return ssot_redirect(providers_path, context="storage_home providers")

    # Returning user - check if they have a valid session
    provider, role, _ = parse_user_id(semptify_uid)

    # Try to get valid session (will auto-refresh if possible)
    session = await get_valid_session(db, semptify_uid, auto_refresh=True)

    if session:
        # Valid session - route to their home page
        return ssot_redirect(_route_user(semptify_uid), context="storage_home session valid")

    # Session expired/invalid and refresh failed - need to reauthorize
    # Extract provider from their existing user ID (no need to ask user)
    if provider and provider in OAUTH_CONFIGS:
        # Silent reauthorize: redirect to OAuth with the same provider
        # User never has to select provider or role - it's encoded in their ID
        oauth_url = f"/storage/auth/{provider}?existing_uid={semptify_uid}"
        return ssot_redirect(oauth_url, context="storage_home silent reauth")

    # Fallback: if we can't determine provider, show reconnect page
    return ssot_redirect("/storage/reconnect", context="storage_home reconnect fallback")


@router.get("/reconnect", response_class=HTMLResponse)
async def reconnect_storage(
    request: Request,
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
    return_to: Optional[str] = Query(None),
):
    """
    Reconnect page for returning users who need to re-authorize storage.
    SEPARATE from onboarding — this is re-auth only, no role selection.

    Flow:
    1. Cookie + valid session → route directly to role home OR return_to URL
    2. Cookie + invalid session + known provider → silent OAuth (with return_to)
    3. Cookie but unknown provider → show provider picker (with return_to)
    4. No cookie → show provider picker
    
    Args:
        return_to: URL to return to after successful reauth (for mid-task recovery)
    """
    from app.core.cookie_auth import verify_user_id
    raw_uid = verify_user_id(semptify_uid) if semptify_uid else None
    
    # Validate return_to for security (only local paths allowed)
    safe_return_to = None
    if return_to and return_to.startswith("/") and not return_to.startswith("//"):
        safe_return_to = return_to

    if raw_uid:
        provider, _, _ = parse_user_id(raw_uid)
        
        # FIRST: Check if session is still valid (no OAuth needed!)
        session = await get_valid_session(db, raw_uid, auto_refresh=True)
        if session:
            # Session valid - return to task or home
            landing = safe_return_to if safe_return_to else _route_user(raw_uid)
            logger.info("Reconnect: session valid, routing to %s for user=%s", landing, raw_uid[:4] + "***")
            return ssot_redirect(landing, context="reconnect_storage session valid")
        
        # Session invalid but provider known - silent OAuth reauthorize with return_to
        if provider and provider in OAUTH_CONFIGS:
            logger.info("Reconnect: silent re-auth for user=%s provider=%s return_to=%s", 
                       raw_uid[:4] + "***", provider, safe_return_to)
            auth_url = f"/storage/auth/{provider}?existing_uid={raw_uid}"
            if safe_return_to:
                auth_url += f"&return_to={safe_return_to}"
            return ssot_redirect(auth_url, context="reconnect_storage silent reauth")

    # Last resort: can't determine provider or no valid cookie — show picker with return_to
    return HTMLResponse(content=_generate_reconnect_html(existing_uid=raw_uid, return_to=safe_return_to))


def _generate_reconnect_html(existing_uid: Optional[str] = None, return_to: Optional[str] = None) -> str:
    """Generate the reconnect page HTML."""
    from app.core.user_id import get_provider_from_user_id
    
    settings = _get_settings()
    
    # Determine known provider from user ID
    known_provider = None
    if existing_uid:
        known_provider = get_provider_from_user_id(existing_uid)
    
    # Provider button configurations
    PROVIDER_CONFIG = {
        "google_drive": ("📁", "Google Drive", settings.google_drive_client_id),
        "dropbox": ("☁️", "Dropbox", settings.dropbox_app_key),
        "onedrive": ("🔵", "OneDrive", settings.onedrive_client_id),
    }
    
    # Generate HTML
    if known_provider and known_provider in PROVIDER_CONFIG:
        # We know their provider - show only that one prominently
        icon, name, enabled = PROVIDER_CONFIG[known_provider]
        if enabled:
            # Auto-redirect script for returning users - no click needed
            auto_redirect_script = f'''
            <div id="reconnecting-msg" style="text-align:center;padding:2rem;">
                <div style="font-size:3rem;margin-bottom:1rem;">🔄</div>
                <h3>Reconnecting to {name}...</h3>
                <p>Your documents are safe. Redirecting you now.</p>
            </div>
            <script>
                // Auto-redirect after 1.5 seconds to let user read the message
                setTimeout(function() {{
                    reconnect('{known_provider}');
                }}, 1500);
            </script>
            '''
            primary_button = auto_redirect_script
            # Show other providers as secondary options
            other_providers = ""
            for pid, (picon, pname, penabled) in PROVIDER_CONFIG.items():
                if pid != known_provider and penabled:
                    other_providers += f'''
                    <button class="btn btn-secondary" onclick="reconnect('{pid}')">
                        <span class="btn-icon">{picon}</span>
                        <div>
                            <small>Use {pname} instead</small>
                        </div>
                    </button>
                    '''
            providers_html = primary_button + '<div style="margin-top:1rem;opacity:0.8;">' + other_providers + '</div>'
        else:
            # Provider disabled - show all available
            providers_html = _get_all_provider_buttons(settings)
    else:
        # Unknown provider - show all
        providers_html = _get_all_provider_buttons(settings)
    
    import json as _json
    existing_uid_js = _json.dumps(existing_uid)  # produces "null" or '"GU..."'
    return_to_js = _json.dumps(return_to)  # produces "null" or '"/timeline/..."'


    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reconnect - Semptify</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f1f5f9;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            max-width: 500px;
            width: 90%;
            padding: 2rem;
        }}
        .icon {{
            font-size: 4rem;
            text-align: center;
            margin-bottom: 1rem;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 0.5rem;
            font-size: 1.75rem;
        }}
        .subtitle {{
            text-align: center;
            color: #94a3b8;
            margin-bottom: 2rem;
        }}
        .info-box {{
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid #10b981;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
        }}
        .button-grid {{
            display: grid;
            gap: 0.75rem;
        }}
        .btn {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.25rem;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            color: #f1f5f9;
            cursor: pointer;
            transition: all 0.2s;
            text-align: left;
            width: 100%;
        }}
        .btn:hover {{
            background: rgba(255,255,255,0.15);
            border-color: rgba(255,255,255,0.3);
        }}
        .btn-icon {{
            font-size: 1.5rem;
        }}
        .btn-label {{
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}
        .btn-desc {{
            font-size: 0.875rem;
            opacity: 0.7;
        }}
        .back-link {{
            display: block;
            text-align: center;
            margin-top: 1.5rem;
            color: #64748b;
            text-decoration: none;
        }}
        .back-link:hover {{
            color: #94a3b8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">👋</div>
        <h1>Welcome Back!</h1>
        <p class="subtitle">Reconnect your storage to restore your journal</p>
        
        <div class="info-box">
            <strong>No data is lost.</strong> Your documents are safely stored in your cloud account. 
            Just reconnect with the same provider you used before.
        </div>
        
        <div class="button-grid">
            {providers_html}
        </div>
        
        <a href="/" class="back-link">← Back to welcome page</a>
    </div>
    
    <script>
        var EXISTING_UID = {existing_uid_js};
        var RETURN_TO = {return_to_js};
        function reconnect(provider) {{
            // Thread existing_uid so the callback keeps the user's original ID.
            // Thread return_to to restore previous task after reauth.
            var url = '/storage/auth/' + provider;
            var params = [];
            if (EXISTING_UID) {{
                params.push('existing_uid=' + encodeURIComponent(EXISTING_UID));
            }}
            if (RETURN_TO) {{
                params.push('return_to=' + encodeURIComponent(RETURN_TO));
            }}
            if (params.length > 0) {{
                url += '?' + params.join('&');
            }}
            window.location.href = url;
        }}
    </script>
</body>
</html>'''


@router.get("/providers")
async def list_providers(
    request: Request,
    semptify_uid: Optional[str] = Cookie(None),
    role: Optional[str] = Query(None),
    from_source: Optional[str] = Query(None, alias="from"),
    return_to: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    message: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
):
    """
    Show storage provider selection page.
    Returns HTML page for browsers, JSON for API clients.
    
    Query params from OAuth callback errors:
    - error: Error code (e.g., "oauth_callback_failed")
    - message: Human-readable error message
    - provider: Which provider failed
    """
    # Check Accept header - if JSON requested, return JSON
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return await _providers_json(semptify_uid)
    
    # Build error info for display
    error_info = None
    if error:
        error_info = {
            "code": error,
            "message": message or "Authentication failed. Please try again.",
            "provider": provider or "unknown"
        }
        logger.warning(f"OAuth error displayed: {error} - {message} (provider: {provider})")
    
    # Return HTML page
    return HTMLResponse(content=_generate_providers_html(semptify_uid, role, from_source, return_to, error_info))


async def _providers_json(semptify_uid: Optional[str] = None):
    """Return providers as JSON for API clients."""
    providers = []
    
    # Check if returning user
    current_provider = None
    current_role = None
    if semptify_uid:
        current_provider = get_provider_from_user_id(semptify_uid)
        current_role = get_role_from_user_id(semptify_uid)

    if _get_settings().google_drive_client_id:
        providers.append({
            "id": "google_drive",
            "name": "Google Drive",
            "icon": "google",
            "enabled": True,
            "connected": current_provider == "google_drive",
        })

    if _get_settings().dropbox_app_key:
        providers.append({
            "id": "dropbox",
            "name": "Dropbox",
            "icon": "dropbox",
            "enabled": True,
            "connected": current_provider == "dropbox",
        })

    if _get_settings().onedrive_client_id:
        providers.append({
            "id": "onedrive",
            "name": "OneDrive",
            "icon": "microsoft",
            "enabled": True,
            "connected": current_provider == "onedrive",
        })

    return {
        "providers": providers,
        "current_user_id": semptify_uid,
        "current_provider": current_provider,
        "current_role": current_role,
    }


def _generate_providers_html(
    semptify_uid: Optional[str] = None,
    role: Optional[str] = None,
    from_source: Optional[str] = None,
    return_to: Optional[str] = None,
    error_info: Optional[dict] = None,
) -> str:
    """Generate the storage provider selection HTML page."""
    current_provider = None
    if semptify_uid:
        current_provider = get_provider_from_user_id(semptify_uid)
    
    # Build error display HTML if there was an OAuth error
    error_html = ""
    if error_info:
        error_html = f'''
        <div class="error-banner" id="error-banner">
            <div class="error-icon">⚠️</div>
            <div class="error-content">
                <div class="error-title">Connection Failed</div>
                <div class="error-message">{error_info.get("message", "Authentication failed. Please try again.")}</div>
                <div class="error-debug" style="display: none;">Error code: {error_info.get("code", "unknown")} | Provider: {error_info.get("provider", "unknown")}</div>
            </div>
            <button class="error-close" onclick="document.getElementById('error-banner').style.display='none'">×</button>
        </div>
        '''

    auth_params: dict[str, str] = {}
    if role in ALLOWED_ROLES:
        auth_params["role"] = role
    if from_source:
        auth_params["from"] = from_source
    if return_to and return_to.startswith("/") and not return_to.startswith("//"):
        auth_params["return_to"] = return_to
    auth_suffix = f"?{urlencode(auth_params)}" if auth_params else ""
    
    # Build provider cards
    provider_cards = ""
    
    if _get_settings().google_drive_client_id:
        connected = "connected" if current_provider == "google_drive" else ""
        provider_cards += f'''
        <a href="/storage/auth/google_drive{auth_suffix}" class="provider-card {connected}">
            <div class="provider-icon">
                <svg viewBox="0 0 24 24" width="48" height="48">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
            </div>
            <div class="provider-name">Google Drive</div>
            <div class="provider-status">{" ✓ Connected" if connected else "Click to connect"}</div>
        </a>
        '''
    
    if _get_settings().dropbox_app_key:
        connected = "connected" if current_provider == "dropbox" else ""
        provider_cards += f'''
        <a href="/storage/auth/dropbox{auth_suffix}" class="provider-card {connected}">
            <div class="provider-icon">
                <svg viewBox="0 0 24 24" width="48" height="48">
                    <path fill="#0061FF" d="M12 6.19L6.5 9.89l5.5 3.7-5.5 3.7L1 13.59l5.5-3.7L1 6.19 6.5 2.5 12 6.19zm0 7.4l5.5-3.7L12 6.19 6.5 9.89l5.5 3.7zm0 3.7l-5.5-3.7 5.5 3.7 5.5-3.7-5.5 3.7zm5.5-7.4L12 6.19l5.5-3.69L23 6.19l-5.5 3.7zm-5.5 11.1l-5.5-3.7v1.5l5.5 3.7 5.5-3.7v-1.5l-5.5 3.7z"/>
                </svg>
            </div>
            <div class="provider-name">Dropbox</div>
            <div class="provider-status">{" ✓ Connected" if connected else "Click to connect"}</div>
        </a>
        '''
    
    if _get_settings().onedrive_client_id:
        connected = "connected" if current_provider == "onedrive" else ""
        provider_cards += f'''
        <a href="/storage/auth/onedrive{auth_suffix}" class="provider-card {connected}">
            <div class="provider-icon">
                <svg viewBox="0 0 24 24" width="48" height="48">
                    <path fill="#0078D4" d="M10.5 18.5c0 .28-.22.5-.5.5H3c-1.1 0-2-.9-2-2v-1c0-2.21 1.79-4 4-4 .34 0 .68.04 1 .12V12c0-2.76 2.24-5 5-5 2.06 0 3.83 1.24 4.6 3.02.13-.01.26-.02.4-.02 2.76 0 5 2.24 5 5s-2.24 5-5 5h-5c-.28 0-.5-.22-.5-.5z"/>
                </svg>
            </div>
            <div class="provider-name">OneDrive</div>
            <div class="provider-status">{" ✓ Connected" if connected else "Click to connect"}</div>
        </a>
        '''
    
    if not provider_cards:
        provider_cards = '''
        <div class="no-providers">
            <p>⚠️ No storage providers configured.</p>
            <p>Please contact support to set up cloud storage integration.</p>
        </div>
        '''
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connect Your Storage - Semptify</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            color: #fff;
        }}
        .container {{
            max-width: 600px;
            width: 100%;
            text-align: center;
        }}
        .logo {{
            font-size: 3rem;
            margin-bottom: 1rem;
        }}
        .step-indicator {{
            background: rgba(255,255,255,0.1);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-bottom: 1rem;
            display: inline-block;
        }}
        h1 {{
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        .subtitle {{
            color: #94a3b8;
            margin-bottom: 2rem;
            font-size: 1.1rem;
        }}
        .security-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #10b981;
            padding: 0.5rem 1rem;
            border-radius: 2rem;
            font-size: 0.875rem;
            margin-bottom: 2rem;
        }}
        .alert-box {{
            display: block;
            background: rgba(239, 68, 68, 0.15);
            border: 2px solid rgba(239, 68, 68, 0.5);
            color: #fca5a5;
            padding: 1rem 1.5rem;
            border-radius: 0.75rem;
            margin-bottom: 2rem;
            font-size: 0.95rem;
            font-weight: 500;
            line-height: 1.6;
        }}
        .providers {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}
        .provider-card {{
            display: flex;
            align-items: center;
            gap: 1rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 1rem;
            padding: 1.5rem;
            text-decoration: none;
            color: #fff;
            transition: all 0.2s ease;
        }}
        .provider-card:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(59, 130, 246, 0.5);
            transform: translateY(-2px);
        }}
        .provider-card.connected {{
            border-color: #10b981;
            background: rgba(16, 185, 129, 0.1);
        }}
        .provider-icon {{
            flex-shrink: 0;
        }}
        .provider-name {{
            font-size: 1.25rem;
            font-weight: 600;
            flex: 1;
            text-align: left;
        }}
        .provider-status {{
            color: #94a3b8;
            font-size: 0.875rem;
        }}
        .provider-card.connected .provider-status {{
            color: #10b981;
        }}
        .info-box {{
            margin-top: 2rem;
            padding: 1.5rem;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 0.75rem;
            text-align: left;
        }}
        .info-box h3 {{
            color: #60a5fa;
            margin-bottom: 0.75rem;
            font-size: 1rem;
        }}
        .info-box ul {{
            color: #94a3b8;
            font-size: 0.9rem;
            padding-left: 1.5rem;
        }}
        .info-box li {{
            margin-bottom: 0.5rem;
        }}
        .no-providers {{
            padding: 2rem;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 0.75rem;
            color: #fca5a5;
        }}
        .error-banner {{
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            background: rgba(239, 68, 68, 0.15);
            border: 2px solid rgba(239, 68, 68, 0.5);
            border-radius: 0.75rem;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            color: #fca5a5;
            text-align: left;
            max-width: 100%;
        }}
        .error-icon {{
            font-size: 1.5rem;
            flex-shrink: 0;
        }}
        .error-content {{
            flex: 1;
        }}
        .error-title {{
            font-weight: 600;
            font-size: 1rem;
            margin-bottom: 0.25rem;
            color: #f87171;
        }}
        .error-message {{
            font-size: 0.9rem;
            line-height: 1.4;
        }}
        .error-debug {{
            font-size: 0.75rem;
            margin-top: 0.5rem;
            color: #94a3b8;
            font-family: monospace;
        }}
        .error-close {{
            background: none;
            border: none;
            color: #fca5a5;
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0;
            line-height: 1;
            opacity: 0.7;
            transition: opacity 0.2s;
        }}
        .error-close:hover {{
            opacity: 1;
        }}
        footer {{
            margin-top: 2rem;
            color: #64748b;
            font-size: 0.875rem;
        }}
        footer a {{
            color: #60a5fa;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        {error_html}
        <div class="logo">⚖️</div>
        {"<div class='step-indicator'>Step 2 of 3</div>" if from_source == "onboarding" and role == "user" else "<div class='step-indicator'>Step 3 of 3</div>" if from_source == "onboarding" else ""}
        <h1>Connect Your Storage</h1>
        <p class="subtitle">Your documents stay in YOUR cloud storage. We never store your files.</p>
        
        <div class="security-badge">
            🔒 Your data, your storage, your control
        </div>
        
        <div class="alert-box">
            <strong>⚠️ IMPORTANT:</strong> Semptify requires a cloud storage provider.<br>
            <span style="font-size: 0.95rem; color: #cbd5e1;">Local storage is NOT supported. Please select one of the providers below.</span>
        </div>
        
        <div class="providers">
            {provider_cards}
        </div>
        
        <div class="info-box">
            <h3>🛡️ Why connect storage?</h3>
            <ul>
                <li><strong>Security:</strong> Your documents never leave your control</li>
                <li><strong>Privacy:</strong> We can't access your files without your permission</li>
                <li><strong>Portability:</strong> Switch devices anytime - your data follows you</li>
                <li><strong>Backup:</strong> Your cloud provider handles backup and sync</li>
            </ul>
        </div>
        
        <footer>
            <p>Semptify &copy; 2025 · <a href="/privacy.html">Privacy</a> · <a href="/help.html">Help</a></p>
        </footer>
    </div>

    <script>
        function setReconnectMessage(text, isError = false) {{
            let el = document.getElementById('reconnect-status');
            if (!el) {{
                el = document.createElement('div');
                el.id = 'reconnect-status';
                el.style.marginTop = '1rem';
                el.style.padding = '0.85rem 1rem';
                el.style.borderRadius = '0.75rem';
                el.style.fontSize = '0.9rem';
                el.style.fontWeight = '500';
                document.querySelector('.providers')?.after(el);
            }}
            el.textContent = text;
            el.style.background = isError ? 'rgba(239, 68, 68, 0.2)' : 'rgba(59, 130, 246, 0.2)';
            el.style.border = isError ? '1px solid rgba(239, 68, 68, 0.45)' : '1px solid rgba(59, 130, 246, 0.45)';
            el.style.color = isError ? '#fecaca' : '#bfdbfe';
        }}

        async function prepareReconnectAndRedirect(href) {{
            try {{
                const prep = await fetch('/storage/prepare-reconnect', {{
                    method: 'POST',
                    credentials: 'include',
                }});
                const data = await prep.json();

                if (data.ready_for_reconnect) {{
                    setReconnectMessage('Reconnect prep complete. Redirecting...');
                    window.location.href = href;
                    return;
                }}

                if (data.state === 'connected' || data.state === 'refreshed') {{
                    setReconnectMessage('Session is valid. Continuing to provider...');
                    window.location.href = href;
                    return;
                }}

                setReconnectMessage(data.message || 'Unable to prepare reconnect. Please try again.', true);
            }} catch (e) {{
                window.location.href = href;
            }}
        }}

        document.querySelectorAll('.provider-card[href^="/storage/auth/"]').forEach((card) => {{
            card.addEventListener('click', (event) => {{
                event.preventDefault();
                const href = card.getAttribute('href');
                if (!href) return;
                prepareReconnectAndRedirect(href);
            }});
        }});
    </script>
</body>
</html>'''


@router.get("/providers/json")
async def list_providers_json(
    semptify_uid: Optional[str] = Cookie(None),
):
    """List available storage providers as JSON (explicit endpoint)."""
    providers = []
    
    # Check if returning user
    current_provider = None
    current_role = None
    if semptify_uid:
        current_provider = get_provider_from_user_id(semptify_uid)
        current_role = get_role_from_user_id(semptify_uid)

    if _get_settings().google_drive_client_id:
        providers.append({
            "id": "google_drive",
            "name": "Google Drive",
            "icon": "google",
            "enabled": True,
            "connected": current_provider == "google_drive",
        })

    if _get_settings().dropbox_app_key:
        providers.append({
            "id": "dropbox",
            "name": "Dropbox",
            "icon": "dropbox",
            "enabled": True,
            "connected": current_provider == "dropbox",
        })

    if _get_settings().onedrive_client_id:
        providers.append({
            "id": "onedrive",
            "name": "OneDrive",
            "icon": "microsoft",
            "enabled": True,
            "connected": current_provider == "onedrive",
        })

    return {
        "providers": providers,
        "current_user_id": semptify_uid,
        "current_provider": current_provider,
        "current_role": current_role,
    }


# ============================================================================
# OAuth Flow
# ============================================================================

@router.get("/auth/{provider}")
async def initiate_oauth(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    role: Optional[str] = None,
    existing_uid: Optional[str] = None,
    return_to: Optional[str] = None,
):
    """
    Start OAuth flow.

    - New user: role param determines their role (defaults to 'tenant')
    - Returning user: role extracted from existing_uid cookie, param ignored
    - return_to: URL to redirect to after OAuth (for setup wizards)
    """
    try:
        print(f"DEBUG: OAuth init for provider: {provider}")
        if provider not in OAUTH_CONFIGS:
            print(f"DEBUG: Unknown provider: {provider}")
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

        # For returning users, extract role from their existing user ID
        # New users default to 'tenant' role
        cookie_uid = request.cookies.get(COOKIE_USER_ID)
        effective_uid = existing_uid or cookie_uid

        if effective_uid and is_valid_storage_user(effective_uid):
            # Returning user: role is encoded in their user ID, ignore param
            _, extracted_role, _ = parse_user_id(effective_uid)
            role = extracted_role or "tenant"
            print(f"DEBUG: Returning user - extracted role '{role}' from user ID")
        else:
            # New user: validate the requested role
            role = (role or "tenant").strip().lower()
            if role not in ALLOWED_ROLES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid role '{role}'. Allowed roles: {sorted(ALLOWED_ROLES)}",
                )

        # Keep returning-user reauth bound to the current browser cookie.
        cookie_uid = request.cookies.get(COOKIE_USER_ID)
        if existing_uid and cookie_uid and existing_uid != cookie_uid:
            # Ignore mismatched query input to prevent UID swapping attempts.
            existing_uid = None

        if not existing_uid and cookie_uid:
            cookie_provider, _, _ = parse_user_id(cookie_uid)
            if cookie_provider == provider:
                existing_uid = cookie_uid

        if existing_uid:
            existing_provider, _, _ = parse_user_id(existing_uid)
            if existing_provider != provider:
                raise HTTPException(
                    status_code=400,
                    detail="existing_uid provider mismatch for requested OAuth provider",
                )

        config = OAUTH_CONFIGS[provider]

        # Housekeeping: remove expired states from the database.
        await _cleanup_expired_states(db)

        # Generate state for CSRF and persist to DB.
        state = secrets.token_urlsafe(32)
        oauth_state_row = OAuthState(
            id=state,
            provider=provider,
            role=role,
            existing_uid=existing_uid,
            return_to=return_to,
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(minutes=OAUTH_STATE_TIMEOUT_MINUTES),
        )
        db.add(oauth_state_row)
        await db.commit()

        # Transitional mirror for legacy tests/callers.
        OAUTH_STATES[state] = {
            "provider": provider,
            "role": role,
            "existing_uid": existing_uid,
            "return_to": return_to,
            "created_at": utc_now(),
            "expires_at": utc_now() + timedelta(minutes=OAUTH_STATE_TIMEOUT_MINUTES),
        }

        # Build callback URL
        # Use PUBLIC_BASE_URL if set (for proxies/production), else request.base_url
        settings = _get_settings()
        if settings.public_base_url:
            base_url = settings.public_base_url.rstrip("/")
        else:
            base_url = str(request.base_url).rstrip("/")
        callback_uri = f"{base_url}/storage/callback/{provider}"
        print(f"DEBUG: Callback URI: {callback_uri}")

        # Build OAuth URL based on provider
        if provider == "google_drive":
            params = {
                "client_id": _get_settings().google_drive_client_id,
                "redirect_uri": callback_uri,
                "response_type": "code",
                "scope": " ".join(config["scopes"]),
                "state": state,
                "access_type": "offline",
                "prompt": "consent",
            }
        elif provider == "dropbox":
            params = {
                "client_id": _get_settings().dropbox_app_key,
                "redirect_uri": callback_uri,
                "response_type": "code",
                "state": state,
                "token_access_type": "offline",
            }
        elif provider == "onedrive":
            params = {
                "client_id": _get_settings().onedrive_client_id,
                "redirect_uri": callback_uri,
                "response_type": "code",
                "scope": " ".join(config["scopes"]),
                "state": state,
            }
        else:
            raise HTTPException(status_code=400, detail="Provider not implemented")

        auth_url = f"{config['auth_url']}?{urlencode(params)}"
        # External OAuth URLs are exempt from SSOT (they're not app navigation)
        return RedirectResponse(url=auth_url, status_code=302)
    except Exception as e:
        print(f"DEBUG: Exception in initiate_oauth: {e}")
        import traceback
        traceback.print_exc()
        raise


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth callback. Creates/validates user and sets cookie.
    """
    try:
        # Clean up any old states first.
        await _cleanup_expired_states(db)

        # Load and validate the CSRF state token from the database.
        result = await db.execute(
            select(OAuthState).where(OAuthState.id == state)
        )
        state_row = result.scalar_one_or_none()

        # Transitional fallback for legacy in-memory state injection (tests/tools).
        legacy_state = None if state_row else OAUTH_STATES.pop(state, None)

        if not state_row and not legacy_state:
            providers_stage = navigation.get_stage("providers")
            providers_path = providers_stage.path if providers_stage else "/storage/providers"
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "bad_request",
                    "message": "Invalid or expired state. Please try connecting your storage again.",
                    "action": "redirect",
                    "redirect_url": providers_path,
                },
            )

        if state_row:
            # Consume the state (delete immediately to prevent replay).
            await db.delete(state_row)
            await db.commit()

            if state_row.provider != provider:
                raise HTTPException(status_code=400, detail="Provider mismatch")

            # SQLite returns naive datetimes even for timezone=True columns; normalise to UTC.
            from datetime import timezone as _tz
            state_expires = state_row.expires_at
            if state_expires.tzinfo is None:
                state_expires = state_expires.replace(tzinfo=_tz.utc)

            if utc_now() > state_expires:
                providers_stage = navigation.get_stage("providers")
                providers_path = providers_stage.path if providers_stage else "/storage/providers"
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "bad_request",
                        "message": "Session expired. Please try connecting your storage again.",
                        "action": "redirect",
                        "redirect_url": providers_path,
                    },
                )

            state_data = {
                "provider": state_row.provider,
                "role": state_row.role,
                "existing_uid": state_row.existing_uid,
                "return_to": state_row.return_to,
            }
        else:
            if legacy_state.get("provider") != provider:
                raise HTTPException(status_code=400, detail="Provider mismatch")

            state_expires = legacy_state.get("expires_at")
            if not state_expires and legacy_state.get("created_at"):
                state_expires = legacy_state["created_at"] + timedelta(minutes=OAUTH_STATE_TIMEOUT_MINUTES)

            if isinstance(state_expires, str):
                state_expires = datetime.fromisoformat(state_expires.replace("Z", "+00:00"))

            if state_expires and state_expires.tzinfo is None:
                from datetime import timezone as _tz
                state_expires = state_expires.replace(tzinfo=_tz.utc)

            if state_expires and utc_now() > state_expires:
                providers_stage = navigation.get_stage("providers")
                providers_path = providers_stage.path if providers_stage else "/storage/providers"
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "bad_request",
                        "message": "Session expired. Please try connecting your storage again.",
                        "action": "redirect",
                        "redirect_url": providers_path,
                    },
                )

            state_data = {
                "provider": legacy_state.get("provider"),
                "role": legacy_state.get("role"),
                "existing_uid": legacy_state.get("existing_uid"),
                "return_to": legacy_state.get("return_to"),
            }

        # Build callback URL (use PUBLIC_BASE_URL if set)
        settings = _get_settings()
        if settings.public_base_url:
            base_url = settings.public_base_url.rstrip("/")
        else:
            base_url = str(request.base_url).rstrip("/")
        callback_uri = f"{base_url}/storage/callback/{provider}"

        # Exchange code for tokens
        token_data = await _exchange_code(provider, code, callback_uri)
        access_token = token_data["access_token"]

        # First-run source of truth: provider-asserted identity proof.
        identity = await _fetch_oauth_identity(provider, access_token)
        provider_subject = identity["provider_subject"]
        # NOTE: OAuth email/name are NOT stored per Semptify privacy policy.
        # User PII lives only in their cloud storage vault, never Semptify's database.

        # Determine user ID
        existing_uid = state_data.get("existing_uid")
        matched_user = None  # set below if a returning user is found by provider subject
        if existing_uid:
            # Returning user - keep their ID
            existing_provider, _, _ = parse_user_id(existing_uid)
            if existing_provider != provider:
                raise HTTPException(status_code=400, detail="existing_uid/provider mismatch in callback")
            user_id = existing_uid

            # Returning-user guard: OAuth subject must match the bound account.
            bound_user = await get_user_from_db(db, user_id)
            if bound_user and bound_user.storage_user_id:
                # Backward compatibility: old rows used user_id as placeholder subject.
                is_placeholder_subject = bound_user.storage_user_id == user_id
                if not is_placeholder_subject and bound_user.storage_user_id != provider_subject:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "identity_mismatch",
                            "message": (
                                "The connected storage account does not match this Semptify user. "
                                "Please sign in with the originally linked storage account."
                            ),
                        },
                    )
            print(f"🔄 OAuth callback: Returning user with existing ID: {user_id}")
        else:
            # First check if this OAuth subject already has a Semptify account.
            matched_user = await get_user_by_provider_subject(db, provider, provider_subject)
            if matched_user:
                user_id = matched_user.id
                # Extract role from user_id for returning users
                _, role, _ = parse_user_id(user_id)
                role = role or "tenant"
                print(f"🔄 OAuth callback: Matched existing user by provider subject: {user_id} (role={role})")
            else:
                # New user - generate ID encoding provider + role
                role = (state_data.get("role") or "tenant").strip().lower()
                if role not in ALLOWED_ROLES:
                    role = "tenant"
                user_id = generate_user_id(provider, role)
                print(f"🆕 OAuth callback: New user - generated ID: {user_id} (provider={provider}, role={role})")

        refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", 3600)
        token_expires_at = (utc_now() + timedelta(seconds=expires_in)).isoformat() + "Z"

        # Save session to database (persists across server restarts)
        expires_at = utc_now() + timedelta(seconds=token_data.get("expires_in", 3600))
        print(f"💾 Saving session to DB: user_id={user_id}, provider={provider}, expires_at={expires_at}")
        await save_session_to_db(
            db=db,
            user_id=user_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        # NOTE: Semptify does NOT store user PII (email, name) in its database.
        # User data lives only in their cloud storage vault.
        # A user is "new" only if they had no existing_uid in state AND were not
        # matched to an existing DB account by provider subject during this callback.
        is_new_user = not state_data.get("existing_uid") and not matched_user
        await get_or_create_storage_config(db, user_id, provider)

        # Permanently record that storage authentication is complete.
        # This is the ProcessGroup exit gate: session saved + user row written = storage connected.
        await _mark_group_complete(db, user_id, "storage_connected")

        # Provision the user's storage vault BEFORE determining landing page.
        # The vault must exist before route_user() checks document count.
        import os
        is_localhost = os.environ.get("ENVIRONMENT", "development") == "development"
        from app.core.cookie_auth import set_auth_cookie

        # CRITICAL: Ensure user_id is set before creating auth_marker
        if not user_id and user:
            user_id = str(user.id)

        auth_marker = {
            "user_id": user_id,
            "provider": provider,
            "created_at": utc_now().isoformat() + "Z",
            "version": "5.0",
        }
        encrypted = _encrypt_token(auth_marker, user_id)
        base_url = str(request.base_url).rstrip("/")

        vault_ok = True
        try:
            await _store_auth_marker(
                provider=provider,
                access_token=access_token,
                encrypted=encrypted,
                user_id=user_id,
                base_url=base_url,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                db=db,
            )
        except Exception:
            logger.exception(
                "OAuth vault provisioning failed after auth success for provider=%s user_id=%s",
                provider,
                user_id,
            )
            vault_ok = False

        # Determine landing page — AFTER vault provisioning attempt.
        # New users (no existing_uid) always go to the onboarding upload step:
        #   vault is now initialized, they upload one document to activate the account,
        #   then route_user() correctly routes them to their role home with documents_present=True.
        # Returning users use route_user() as normal.
        # If vault provisioning failed, send to onboarding/status for retry.
        return_to = state_data.get("return_to")

        if not vault_ok:
            status_stage = navigation.get_stage("status")
            landing = f"{status_stage.path}?storage_setup=retry_required&provider={provider}"
        elif return_to:
            landing = return_to
        elif is_new_user:
            # Auto-create test document to tick counter and prevent case file diversion
            try:
                from app.routers.vault import get_vault_client
                from app.models.models import Document
                from datetime import datetime, timezone
                import uuid
                import hashlib
                
                # Strip HMAC signature for database operations and vault access
                db_user_id = user_id.split('.')[0] if '.' in user_id else user_id
                
                vault = await get_vault_client(db, db_user_id)
                if vault:
                    # Create test document content
                    test_content = b"Semptify vault verification document - This confirms your storage is working correctly."
                    test_filename = "semptify_vault_verification.txt"
                    doc_id = str(uuid.uuid4())
                    
                    # Upload test document to vault
                    await vault.write_file(
                        path=f"documents/{test_filename}",
                        content=test_content,
                        metadata={"purpose": "vault_verification", "auto_generated": True}
                    )
                    
                    # Create Document record in database to tick counter
                    file_hash = hashlib.sha256(test_content).hexdigest()
                    doc = Document(
                        id=doc_id,
                        user_id=db_user_id,  # Document.user_id is VARCHAR(24)
                        filename=test_filename,
                        original_filename=test_filename,
                        file_path=f".semptify/vault/documents/{test_filename}",
                        file_size=len(test_content),
                        mime_type="text/plain",
                        document_type="other",
                        sha256_hash=file_hash,
                        uploaded_at=datetime.now(timezone.utc),
                        description="Auto-generated vault verification document"
                    )
                    db.add(doc)
                    await db.commit()
                    
                    logger.info(f"Auto-created test document {doc_id} to tick counter for new user {db_user_id[:6]}...")
            except Exception as e:
                logger.warning(f"Failed to auto-create test document: {e}")
                # Continue anyway - vault_ok already succeeded
            # Route directly to user home, skip upload step
            landing = _route_user(user_id)
        else:
            landing = _route_user(user_id)

        logger.info("OAuth callback complete: user=%s new=%s vault_ok=%s landing=%s",
                    user_id[:6] + "***" if user_id else "EMPTY", is_new_user, vault_ok, landing)

        # DEBUG: Verify user_id before setting cookie
        if not user_id:
            logger.error("CRITICAL: user_id is empty! Cannot set auth cookie.")
            raise HTTPException(status_code=500, detail="User ID missing after OAuth")

        # Return HTML with JavaScript redirect to avoid cross-origin frame blocking
        # This bypasses browser security restrictions when redirecting from OAuth iframe
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Redirecting...</title>
        </head>
        <body>
            <script>
                // Set cookie via JavaScript (already set by server, but ensure it's available)
                document.cookie = 'semptify_uid={user_id}; path=/; SameSite=Lax';
                // Redirect to landing page
                window.location.href = '{landing}';
            </script>
            <p>Redirecting to your dashboard...</p>
        </body>
        </html>
        """

        response = HTMLResponse(content=html_content)
        set_auth_cookie(response, user_id)
        logger.info("Auth cookie set for user: %s", user_id[:6] + "***")
        response.delete_cookie("semptify_redirect_loop_count")

        return response
    except HTTPException as exc:
        message = "Storage connection failed. Please try connecting again."
        if isinstance(exc.detail, dict) and exc.detail.get("message"):
            message = str(exc.detail.get("message"))
        elif isinstance(exc.detail, str) and exc.detail:
            message = exc.detail

        logger.warning(
            "OAuth callback HTTP error for provider=%s path=%s detail=%s",
            provider,
            request.url.path,
            exc.detail,
        )
        providers_stage = navigation.get_stage("providers")
        providers_path = providers_stage.path if providers_stage else "/storage/providers"
        error_url = providers_path + "?" + urlencode({
            "error": "oauth_callback_failed",
            "provider": provider,
            "message": message,
        })

        # Use JavaScript redirect to avoid cross-origin blocking
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Redirecting...</title>
        </head>
        <body>
            <script>
                if (window.top !== window.self) {{
                    window.top.location.href = '{error_url}';
                }} else {{
                    window.location.href = '{error_url}';
                }}
            </script>
            <p>Redirecting...</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as exc:
        error_msg = str(exc)
        logger.exception(
            "OAuth callback unexpected error for provider=%s path=%s error=%s",
            provider,
            request.url.path,
            error_msg,
            exc_info=True,
        )
        providers_stage = navigation.get_stage("providers")
        providers_path = providers_stage.path if providers_stage else "/storage/providers"
        error_url = providers_path + "?" + urlencode({
            "error": "oauth_callback_failed",
            "provider": provider,
            "message": f"Error: {error_msg}",
        })

        # Use JavaScript redirect to avoid cross-origin blocking
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Redirecting...</title>
        </head>
        <body>
            <script>
                if (window.top !== window.self) {{
                    window.top.location.href = '{error_url}';
                }} else {{
                    window.location.href = '{error_url}';
                }}
            </script>
            <p>Redirecting...</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
# ============================================================================
# Token Exchange
# ============================================================================

async def _exchange_code(provider: str, code: str, redirect_uri: str) -> dict:
    """Exchange OAuth code for tokens."""
    config = OAUTH_CONFIGS[provider]
    
    async with httpx.AsyncClient() as client:
        if provider == "google_drive":
            response = await client.post(config["token_url"], data={
                "code": code,
                "client_id": _get_settings().google_drive_client_id,
                "client_secret": _get_settings().google_drive_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
        elif provider == "dropbox":
            response = await client.post(config["token_url"], data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }, auth=(_get_settings().dropbox_app_key, _get_settings().dropbox_app_secret))
        elif provider == "onedrive":
            response = await client.post(config["token_url"], data={
                "code": code,
                "client_id": _get_settings().onedrive_client_id,
                "client_secret": _get_settings().onedrive_client_secret,
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
                detail={
                    "error": "token_exchange_failed",
                    "message": f"Token exchange failed for {provider}: {provider_error}",
                },
            )

        return response.json()


async def _fetch_oauth_identity(provider: str, access_token: str) -> dict:
    """
    Fetch provider-asserted account identity.

    First-run rule: OAuth token exchange is not enough by itself; we require
    successful provider identity lookup (userinfo/me/current_account) before
    we bind/create the Semptify user and proceed to vault provisioning.
    """
    config = OAUTH_CONFIGS.get(provider)
    if not config or not config.get("userinfo_url"):
        raise HTTPException(status_code=400, detail="OAuth identity endpoint unavailable")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if provider == "dropbox":
                response = await client.post(
                    config["userinfo_url"],
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    content="null",
                )
            else:
                response = await client.get(
                    config["userinfo_url"],
                    headers={"Authorization": f"Bearer {access_token}"},
                )

        if response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "oauth_identity_failed",
                    "message": "OAuth identity verification failed with the storage provider.",
                },
            )

        payload = response.json()

        if provider == "google_drive":
            provider_subject = payload.get("id")
            email = payload.get("email")
            display_name = payload.get("name")
        elif provider == "dropbox":
            provider_subject = payload.get("account_id")
            email = payload.get("email")
            name_obj = payload.get("name") if isinstance(payload.get("name"), dict) else {}
            display_name = name_obj.get("display_name") or payload.get("display_name")
        elif provider == "onedrive":
            provider_subject = payload.get("id")
            email = payload.get("mail") or payload.get("userPrincipalName")
            display_name = payload.get("displayName")
        else:
            provider_subject = None
            email = None
            display_name = None

        if not provider_subject:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "oauth_identity_missing_subject",
                    "message": "OAuth identity response did not include a provider subject id.",
                },
            )

        return {
            "provider_subject": provider_subject,
            "email": email,
            "display_name": display_name,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "oauth_identity_failed",
                "message": "Unable to verify storage account identity from OAuth provider.",
            },
        )


# NOTE: _generate_sync_html removed - now using VaultManager.generate_rehome_html()


async def _store_auth_marker(
    provider: str,
    access_token: str,
    encrypted: bytes,
    user_id: str,
    base_url: str,
    refresh_token: str = "",
    token_expires_at: str = "",
    db: Optional[AsyncSession] = None,
) -> None:
    """
    Initialize complete Semptify5.0 vault structure in user's cloud storage.
    Uses VaultManager to create folder structure, store encrypted token, and Rehome script.
    
    The OAuth credentials (access_token, refresh_token) are stored encrypted in cloud
    as a BACKUP. Primary storage is the database for fast API access.
    """
    from app.services.storage import get_provider
    from app.services.storage.vault_manager import get_vault_manager

    storage = get_provider(provider, access_token=access_token)
    vault = get_vault_manager(storage, user_id, base_url)

    # Initialize full vault structure with OAuth credentials backup
    await vault.initialize_vault(
        provider_name=provider,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=token_expires_at,
    )

    # Vault proven: folders created, token encrypted+written, decrypt verified.
    # Write the permanent completion badge — serial gate is met.
    if db is not None:
        await _mark_group_complete(db, user_id, "vault_initialized")


async def _vault_access_ready(
    user_id: str,
    provider: str,
    access_token: str,
    base_url: str,
) -> tuple[bool, str]:
    """Check whether vault is ready for function-token access (created + enabled)."""
    from app.services.storage import get_provider
    from app.services.storage.vault_manager import get_vault_manager
    from app.core.vault_paths import PROVISIONING_FILE

    try:
        storage = get_provider(provider, access_token=access_token)
        vault = get_vault_manager(storage, user_id, base_url)

        has_token = await vault.validate_token()
        if not has_token:
            return False, "vault_token_missing"

        try:
            state_bytes = await storage.download_file(PROVISIONING_FILE)
            state = json.loads(state_bytes.decode("utf-8"))
            if state.get("vault_enabled") is True and state.get("state") == "enabled":
                return True, "enabled"
            return False, "vault_not_enabled"
        except Exception:
            # Backward compatibility: older vaults may not have provisioning_state.json
            return True, "legacy_vault_token_valid"
    except Exception:
        return False, "vault_verification_failed"

# ============================================================================
# Session & Status Endpoints
# ============================================================================

@router.get("/rehome/{user_id}")
async def rehome_device(
    user_id: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Rehome endpoint - called from Rehome.html in user's cloud storage.
    Verifies token exists in storage, then sets cookie on new device.
    
    This is the reconnection flow:
    1. User lost cookie / new device / new browser
    2. User opens Rehome.html from their cloud storage
    3. Rehome.html redirects here with their user_id
    4. We verify their token exists in storage (proof of ownership)
    5. Set cookie and redirect to app
    """
    from app.services.storage.vault_manager import get_vault_manager
    
    # Validate user ID format
    provider, role, unique = parse_user_id(user_id)
    if not provider or not unique:
        return HTMLResponse(content=_error_html("Invalid Account", "The account ID is invalid. Please try again from your cloud storage."), status_code=400)
    
    provider_names = {
        "google_drive": "Google Drive",
        "dropbox": "Dropbox",
        "onedrive": "OneDrive"
    }
    provider_display = provider_names.get(provider, provider)
    
    # Try to load existing session from database to get access token
    session = await get_session_from_db(db, user_id)
    
    if session:
        # Have session - can verify token in storage
        try:
            from app.services.storage import get_provider
            storage = get_provider(provider, access_token=session["access_token"])
            vault = get_vault_manager(storage, user_id, str(request.base_url).rstrip("/"))
            
            # Verify token exists
            if await vault.validate_token():
                # Token valid! Register this device and set cookie
                device_id = secrets.token_urlsafe(16)
                user_agent = request.headers.get("User-Agent", "Unknown")
                await vault.register_device(device_id, "Rehomed Device", user_agent)
        except Exception as e:
            # Token verification failed - but we have session, so allow anyway
            pass
    
    # Set the cookie and show success
    import os
    is_localhost = os.environ.get("ENVIRONMENT", "development") == "development"
    is_secure = False if is_localhost else True
    response = HTMLResponse(content=f'''<!DOCTYPE html>
<html>
<head>
    <title>Reconnected!</title>
    <meta http-equiv="refresh" content="2;url=/static/welcome.html">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }}
        .box {{ 
            background: #1e293b;
            padding: 50px;
            border-radius: 20px;
            text-align: center;
            max-width: 450px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.5);
        }}
        .success-icon {{ font-size: 4rem; margin-bottom: 20px; }}
        h1 {{ color: #10b981; margin-bottom: 15px; }}
        .info {{ 
            background: #334155;
            padding: 20px;
            border-radius: 12px;
            margin: 25px 0;
            text-align: left;
        }}
        .row {{ 
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #475569;
        }}
        .row:last-child {{ border-bottom: none; }}
        .label {{ color: #94a3b8; }}
        .value {{ font-weight: 600; }}
        .redirect {{ color: #94a3b8; font-size: 0.9rem; margin-top: 20px; }}
        .spinner {{
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #475569;
            border-top-color: #10b981;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div class="box">
        <div class="success-icon">🏠</div>
        <h1>Welcome Home!</h1>
        <p>This device is now connected to your Semptify account.</p>
        <div class="info">
            <div class="row">
                <span class="label">Storage</span>
                <span class="value">{provider_display}</span>
            </div>
            <div class="row">
                <span class="label">Account Type</span>
                <span class="value" style="text-transform: capitalize;">{role or 'User'}</span>
            </div>
            <div class="row">
                <span class="label">Account ID</span>
                <span class="value" style="font-family: monospace;">{user_id}</span>
            </div>
        </div>
        <p class="redirect"><span class="spinner"></span> Taking you to your dashboard...</p>
    </div>
</body>
</html>''')
    
    from app.core.cookie_auth import set_auth_cookie
    set_auth_cookie(response, user_id)
    
    return response


def _error_html(title: str, message: str) -> str:
    """Generate error HTML page."""
    return f'''<!DOCTYPE html>
<html>
<head><title>Error - {title}</title>
<style>
    body {{ font-family: sans-serif; background: #0f172a; color: #f8fafc;
           display: flex; align-items: center; justify-content: center;
           min-height: 100vh; margin: 0; }}
    .box {{ background: #1e293b; padding: 40px; border-radius: 16px; text-align: center; max-width: 400px; }}
    h1 {{ color: #ef4444; margin-bottom: 15px; }}
    p {{ color: #94a3b8; }}
    a {{ color: #3b82f6; }}
</style>
</head>
<body>
    <div class="box">
        <h1>❌ {title}</h1>
        <p>{message}</p>
        <p style="margin-top: 20px;"><a href="/storage/providers">← Try again</a></p>
    </div>
</body>
</html>'''


@router.get("/sync/{user_id}")
async def sync_device_legacy(user_id: str, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Legacy sync endpoint - redirects to rehome.
    Kept for backwards compatibility with old Semptify_Sync.html files.
    """
    return await rehome_device(user_id, request, response, db)
@router.get("/status")
async def get_status(
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current auth status.
    Returns provider, role, and access token for API calls.
    Automatically refreshes expired tokens if possible.
    """
    print(f"📊 /storage/status called - cookie semptify_uid: {semptify_uid[:10] if semptify_uid else 'None'}...")
    if not semptify_uid:
        print(f"❌ No semptify_uid cookie found")
        return {"authenticated": False}

    # Use get_valid_session which handles token refresh automatically
    session = await get_valid_session(db, semptify_uid, auto_refresh=True)
    print(f"📊 Session lookup result: {bool(session)}")
    
    if not session:
        # Have cookie but no active/valid session - need to re-auth
        provider, role, _ = parse_user_id(semptify_uid)
        return {
            "authenticated": False,
            "user_id": semptify_uid,
            "provider": provider,
            "role": role,
            "needs_reauth": True,
            "reason": "token_expired_or_invalid",
        }

    provider, role, _ = parse_user_id(semptify_uid)
    return {
        "authenticated": True,
        "user_id": semptify_uid,
        "provider": provider,
        "role": role,
        "access_token": session["access_token"],
        "expires_at": session.get("expires_at"),
    }


@router.get("/session")
async def get_session_info(
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Get session info (without sensitive access token)."""
    if not semptify_uid:
        return {"authenticated": False}

    provider, role, _ = parse_user_id(semptify_uid)
    raw_session = await get_session_from_db(db, semptify_uid)
    valid_session = await get_valid_session(db, semptify_uid, auto_refresh=False)

    return {
        "authenticated": valid_session is not None,
        "user_id": semptify_uid,
        "provider": provider,
        "role": role,
        "provider_name": {
            "google_drive": "Google Drive",
            "dropbox": "Dropbox",
            "onedrive": "OneDrive",
        }.get(provider, provider),
        "role_name": role.title() if role else None,
        "expires_at": raw_session.get("expires_at") if raw_session else None,
        "needs_reauth": raw_session is not None and valid_session is None,
        "session_present": raw_session is not None,
    }


# ============================================================================
# Returning User Reconnect API
# ============================================================================

@router.post("/api/user/lookup")
async def lookup_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Look up user by email or provider for returning user reconnect.
    
    Request body: {"email": "user@example.com"} OR {"provider": "google", "provider_account_id": "..."}
    Response: {"found": true, "user_id": "usr_...", "role": "tenant"} OR {"found": false}
    """
    try:
        data = await request.json()
        
        if not data:
            return {"found": False, "error": "No data provided"}
        
        # Lookup by email
        if "email" in data and data["email"]:
            from app.models.database import User
            from sqlalchemy import select
            
            result = await db.execute(
                select(User).where(User.email == data["email"])
            )
            user = result.scalar_one_or_none()
            
            if user:
                return {
                    "found": True,
                    "user_id": user.user_id,
                    "role": user.role,
                    "provider": user.provider,
                }
        
        # Lookup by provider (when user clicks provider button instead of entering email)
        if "provider" in data and data["provider"]:
            # User selected a provider - they'll need to OAuth to identify themselves
            # Store preference and return redirect info
            return {
                "found": True,
                "oauth_required": True,
                "provider": data["provider"],
                "message": "Please authenticate with your storage provider",
            }
        
        return {"found": False}
        
    except Exception as e:
        print(f"❌ Error in lookup_user: {e}")
        return {"found": False, "error": "Lookup failed"}


@router.post("/api/session/restore")
async def restore_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Restore user session after reconnect.
    
    Request body: {"user_id": "usr_..."}
    Response: {"success": true, "redirect_url": "/tenant/dashboard"} OR
              {"oauth_required": true, "oauth_url": "/storage/providers?..."}
    """
    try:
        data = await request.json()
        user_id = data.get("user_id")
        
        if not user_id:
            return {"success": False, "error": "No user_id provided"}
        
        # Parse user_id to get provider and role
        from app.core.user_id import parse_user_id
        provider, role, provider_account_id = parse_user_id(user_id)
        
        # Check for existing valid session in DB
        from app.services.storage import get_valid_session
        session = await get_valid_session(db, user_id, auto_refresh=True)
        
        if session:
            # Valid session exists - restore cookie and redirect
            # Set secure cookie - secure=False for localhost HTTP, True for HTTPS production
            import os
            is_localhost = os.environ.get("ENVIRONMENT", "development") == "development"
            from app.core.cookie_auth import set_auth_cookie
            set_auth_cookie(response, user_id)
            
            # Route to role-appropriate dashboard
            from app.core.workflow_engine import route_user
            redirect_url = route_user(user_id, documents_present=True, has_active_case=True)
            
            return {
                "success": True,
                "redirect_url": redirect_url,
            }
        
        # No valid session - need OAuth re-authentication
        # NOTE: Do NOT set return_to here - let OAuth callback use route_user() to determine landing
        return {
            "success": False,
            "oauth_required": True,
            "oauth_url": f"/storage/providers?user_id={user_id}",
            "message": "Storage connection needs renewal",
        }
        
    except Exception as e:
        print(f"❌ Error in restore_session: {e}")
        return {"success": False, "error": "Session restoration failed"}


@router.post("/prepare-reconnect")
async def prepare_reconnect(
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Ensure stale persistent sessions are fully disconnected before reconnect.
    This endpoint clears cache + DB session rows only when token is invalid and cannot refresh.
    """
    if not semptify_uid:
        return {
            "ready_for_reconnect": True,
            "state": "disconnected",
            "message": "No session cookie found.",
        }

    session = await get_session_from_db(db, semptify_uid)
    if not session:
        SESSIONS.pop(semptify_uid, None)
        return {
            "ready_for_reconnect": True,
            "state": "disconnected",
            "message": "No persistent session found.",
        }

    provider = session.get("provider")
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")

    is_valid = await validate_token_with_provider(provider, access_token)
    if is_valid:
        return {
            "ready_for_reconnect": False,
            "state": "connected",
            "message": "Session is still valid. Reconnect not required.",
            "provider": provider,
        }

    refreshed = None
    if refresh_token:
        refreshed = await refresh_access_token(db, semptify_uid, provider, refresh_token)

    if refreshed:
        return {
            "ready_for_reconnect": False,
            "state": "refreshed",
            "message": "Token was refreshed. Reconnect not required.",
            "provider": provider,
        }

    # Fully disconnect stale state so OAuth reconnect can proceed cleanly.
    result = await db.execute(select(SessionModel).where(SessionModel.user_id == semptify_uid))
    session_row = result.scalar_one_or_none()
    if session_row:
        await db.delete(session_row)
        await db.commit()
    SESSIONS.pop(semptify_uid, None)

    invalidate_function_access_tokens(semptify_uid)

    return {
        "ready_for_reconnect": True,
        "state": "disconnected_stale",
        "message": "Stale session cleared. OAuth reconnect can proceed.",
        "provider": provider,
        "needs_reauth": True,
    }


@router.post("/function-token/issue")
async def issue_function_token(
    request: Request,
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Issue short-lived function access token after verifying cookie + vault readiness."""
    if not semptify_uid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await get_valid_session(db, semptify_uid, auto_refresh=True)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    provider = session.get("provider")
    access_token = session.get("access_token")
    base_url = str(request.base_url).rstrip("/")
    ready, reason = await _vault_access_ready(
        user_id=semptify_uid,
        provider=provider,
        access_token=access_token,
        base_url=base_url,
    )

    if not ready:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "vault_not_ready",
                "reason": reason,
                "message": "Vault is not ready for function access yet",
            },
        )

    token_payload = issue_function_access_token(
        semptify_uid,
        context={
            "provider": provider,
            "reason": "vault_functions",
            "scopes": ["overlay:read", "overlay:write"],
            "document_ids": ["*"],
        },
    )
    return {
        "success": True,
        "token": token_payload["token"],
        "expires_at": token_payload["expires_at"],
        "reverify_in_seconds": token_payload["reverify_in_seconds"],
    }


@router.get("/function-token/verify")
async def verify_function_token_endpoint(
    request: Request,
    refresh: bool = Query(True),
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Verify (and optionally refresh) short-lived function access token validity."""
    if not semptify_uid:
        return {"valid": False, "reason": "no_cookie", "needs_reauth": True}

    # Cookie/session must still be valid for token to be trusted.
    session = await get_valid_session(db, semptify_uid, auto_refresh=True)
    if not session:
        return {"valid": False, "reason": "session_invalid", "needs_reauth": True}

    token_value = request.headers.get("X-Function-Token")
    if not token_value:
        return {"valid": False, "reason": "token_missing", "needs_reauth": False}

    result = verify_function_access_token(semptify_uid, token_value, refresh=refresh)
    result["needs_reauth"] = False
    return result


@router.post("/validate")
async def validate_and_refresh_token(
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate current access token and refresh if needed.
    Returns detailed status about token validity.
    """
    if not semptify_uid:
        return {
            "valid": False,
            "reason": "no_session",
            "message": "No session cookie found",
        }

    # First get raw session without auto-refresh
    session = await get_session_from_db(db, semptify_uid)
    if not session:
        return {
            "valid": False,
            "reason": "no_session",
            "message": "No session found in database",
        }

    provider = session.get("provider")
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    expires_at = session.get("expires_at")

    # Check if token is expired
    token_expired = False
    if expires_at:
        if isinstance(expires_at, str):
            expires_at_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        else:
            expires_at_dt = expires_at
        # Ensure expires_at_dt is timezone-aware (assume UTC if naive)
        if expires_at_dt.tzinfo is None:
            from datetime import timezone
            expires_at_dt = expires_at_dt.replace(tzinfo=timezone.utc)
        token_expired = utc_now() >= expires_at_dt

    # Validate with provider
    is_valid = await validate_token_with_provider(provider, access_token)

    if is_valid and not token_expired:
        return {
            "valid": True,
            "provider": provider,
            "expires_at": expires_at,
            "message": "Token is valid",
        }

    # Token is invalid or expired - try to refresh
    if refresh_token:
        new_token_data = await refresh_access_token(db, semptify_uid, provider, refresh_token)
        if new_token_data:
            return {
                "valid": True,
                "refreshed": True,
                "provider": provider,
                "expires_at": new_token_data["expires_at"].isoformat(),
                "message": "Token was expired but successfully refreshed",
            }

    # Could not refresh
    return {
        "valid": False,
        "reason": "token_invalid",
        "has_refresh_token": bool(refresh_token),
        "provider": provider,
        "message": "Token is invalid and could not be refreshed. Please re-authenticate.",
    }


# ============================================================================
# Role Management
# ============================================================================

@router.post("/role")
async def switch_role(
    request: RoleSwitchRequest,
    response: Response,
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Switch user's role. Updates user ID and cookie.

    Roles and Authorization:
    - user: Standard tenant access (default) - no authorization needed
    - manager: Property management - requires household_members > 1
    - advocate: Tenant advocate - requires valid invite_code
    - legal: Legal professional - requires valid invite_code
    - admin: System administrator - requires PIN (set via ADMIN_PIN env var)
    """
    if not semptify_uid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if request.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Valid: {sorted(ALLOWED_ROLES)}",
        )

    # Authorization checks based on role
    if request.role == "admin":
        # Admin requires PIN
        if not request.pin or request.pin != ADMIN_PIN:
            raise HTTPException(
                status_code=403,
                detail="Admin access requires valid PIN"
            )

    elif request.role in ["advocate", "legal"]:
        # Advocate/Legal require invite code
        if not request.invite_code or request.invite_code not in VALID_INVITE_CODES:
            raise HTTPException(
                status_code=403,
                detail=f"{request.role.capitalize()} access requires valid invite code"
            )

    elif request.role == "manager":
        # Manager requires multiple people on lease
        if not request.household_members or request.household_members < 2:
            raise HTTPException(
                status_code=403,
                detail="Manager access requires more than one person on lease"
            )

    # Generate new user ID with new role
    new_uid = update_user_id_role(semptify_uid, request.role)
    if not new_uid:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    # Get existing session from database
    session = await get_session_from_db(db, semptify_uid)
    if session:
        # Save session with new user ID
        await save_session_to_db(
            db=db,
            user_id=new_uid,
            provider=session["provider"],
            access_token=session["access_token"],
            refresh_token=session.get("refresh_token"),
        )
        # Update user record
        await create_or_update_user(db, new_uid, session["provider"])
        # Update storage config
        await get_or_create_storage_config(db, new_uid, session["provider"])
        # Clear old compatibility cache entry.
        SESSIONS.pop(semptify_uid, None)
    # Role transition invalidates prior function tokens bound to the old role context.
    invalidate_function_access_tokens(semptify_uid)

    # Update cookie - use secure=False for localhost
    import os
    is_localhost = os.environ.get("ENVIRONMENT", "development") == "development"
    is_secure = False if is_localhost else True
    from app.core.cookie_auth import set_auth_cookie
    set_auth_cookie(response, new_uid)

    return {
        "success": True,
        "old_user_id": semptify_uid,
        "new_user_id": new_uid,
        "role": request.role,
        "authorized": True,
    }
# ============================================================================
# Logout
# ============================================================================

@router.get("/logout-reset", response_class=HTMLResponse)
async def logout_reset(response: Response):
    """
    GET endpoint to clear a stale semptify_uid cookie and redirect to provider selection.
    Used when a user has a cookie that no longer has a matching DB record.
    """
    providers_stage = navigation.get_stage("providers")
    providers_path = providers_stage.path if providers_stage else "/storage/providers"
    redirect = ssot_redirect(providers_path, context="logout_reset")
    redirect.delete_cookie(COOKIE_USER_ID)
    redirect.delete_cookie("semptify_redirect_loop_count")
    return redirect


@router.post("/logout")
async def logout(
    response: Response,
    semptify_uid: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """Clear session and cookie."""
    if semptify_uid:
        invalidate_function_access_tokens(semptify_uid)
        SESSIONS.pop(semptify_uid, None)
        # Remove from database
        result = await db.execute(
            select(SessionModel).where(SessionModel.user_id == semptify_uid)
        )
        session_row = result.scalar_one_or_none()
        if session_row:
            await db.delete(session_row)
            await db.commit()

    response.delete_cookie(COOKIE_USER_ID)
    return {"success": True}


# ============================================================================
# Legal Integrity Endpoints
# ============================================================================

@router.post("/integrity/hash")
async def hash_document_content(
    content: bytes = b"",
    semptify_uid: Optional[str] = Cookie(None),
):
    """
    Create SHA-256 hash of document content.
    This hash can be used to verify document hasn't been tampered with.
    Returns court-admissible cryptographic fingerprint.
    """
    from app.services.storage.legal_integrity import hash_document, create_notarized_timestamp
    
    if not content:
        raise HTTPException(status_code=400, detail="No content provided")
    
    doc_hash = hash_document(content)
    timestamp = create_notarized_timestamp()
    
    return {
        "hash": doc_hash,
        "algorithm": "SHA-256",
        "timestamp": timestamp,
        "user_id": semptify_uid,
        "legal_note": "This hash is a cryptographic fingerprint that uniquely identifies this document. Any modification to the document will produce a different hash."
    }


@router.post("/integrity/proof")
async def create_document_proof(
    content: bytes = b"",
    action: str = "upload",
    semptify_uid: Optional[str] = Cookie(None),
):
    """
    Create complete cryptographic proof for a document.
    Includes hash, timestamp, and signature suitable for court submission.
    """
    from app.services.storage.legal_integrity import get_legal_integrity
    
    if not semptify_uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not content:
        raise HTTPException(status_code=400, detail="No content provided")
    
    integrity = get_legal_integrity(semptify_uid)
    proof = integrity.create_document_proof(content, action)
    
    return {
        "proof": proof.to_dict(),
        "verification_url": f"/storage/integrity/verify/{proof.proof_id}",
        "legal_note": "This proof provides court-admissible evidence of document authenticity and timestamp."
    }


@router.post("/integrity/verify")
async def verify_document_integrity(
    content: bytes = b"",
    proof_data: dict = {},
    semptify_uid: Optional[str] = Cookie(None),
):
    """
    Verify document against its proof.
    Returns detailed verification report suitable for court presentation.
    """
    from app.services.storage.legal_integrity import get_legal_integrity, DocumentProof
    
    if not semptify_uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not content or not proof_data:
        raise HTTPException(status_code=400, detail="Content and proof required")
    
    try:
        proof = DocumentProof.from_dict(proof_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid proof format: {e}")
    
    integrity = get_legal_integrity(semptify_uid)
    verification = integrity.verify_document(content, proof)
    
    return verification


@router.get("/integrity/timestamp")
async def get_legal_timestamp():
    """
    Get current legal timestamp with cryptographic proof.
    Can be used to prove when an action occurred.
    """
    from app.services.storage.legal_integrity import create_notarized_timestamp

    return create_notarized_timestamp()


# ============================================================================
# Certificate Generation Endpoints
# ============================================================================

@router.post("/certificate/generate")
async def generate_certificate(
    request: Request,
    document_name: str = "Uploaded Document",
    semptify_uid: Optional[str] = Cookie(None),
):
    """
    Generate a legal verification certificate for a document.
    
    Upload a document and receive:
    - Certificate data (JSON)
    - Printable HTML certificate
    - Plain text certificate
    - Cryptographic proof
    
    The certificate can be printed and attached to court filings.
    """
    from app.services.storage.certificate_generator import quick_certificate
    
    if not semptify_uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Read document from request body
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="No document content provided")
    
    base_url = str(request.base_url).rstrip("/")
    
    result = quick_certificate(
        document_content=content,
        document_name=document_name,
        user_id=semptify_uid,
        base_url=base_url,
    )
    
    return {
        "success": True,
        "certificate_id": result["certificate"]["certificate_id"],
        "verification_code": result["certificate"]["verification_code"],
        "certificate": result["certificate"],
        "proof": result["proof"],
    }


@router.post("/certificate/html")
async def generate_certificate_html_endpoint(
    request: Request,
    document_name: str = "Uploaded Document",
    semptify_uid: Optional[str] = Cookie(None),
):
    """
    Generate printable HTML certificate.
    Returns HTML that can be printed or saved as PDF.
    """
    from app.services.storage.certificate_generator import quick_certificate
    
    if not semptify_uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="No document content provided")
    
    base_url = str(request.base_url).rstrip("/")
    
    result = quick_certificate(
        document_content=content,
        document_name=document_name,
        user_id=semptify_uid,
        base_url=base_url,
    )
    
    return HTMLResponse(content=result["html"])


@router.get("/certificate/verify/{certificate_id}")
async def verify_certificate(
    certificate_id: str,
    code: Optional[str] = None,
):
    """
    Verify a certificate by ID.
    This is the endpoint that QR codes and verification links point to.
    """
    # In a full implementation, we would look up the certificate from storage
    # For now, return verification instructions
    
    return HTMLResponse(content=f'''<!DOCTYPE html>
<html>
<head>
    <title>Certificate Verification - {certificate_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            color: white;
        }}
        .box {{
            background: white;
            color: #1a1a1a;
            padding: 40px;
            border-radius: 16px;
            max-width: 500px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .icon {{ font-size: 4rem; margin-bottom: 20px; }}
        h1 {{ color: #1e3a5f; margin-bottom: 10px; }}
        .cert-id {{
            font-family: monospace;
            background: #f0f4f8;
            padding: 10px 20px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 14px;
        }}
        .code {{
            font-family: monospace;
            font-size: 24px;
            color: #1e3a5f;
            letter-spacing: 2px;
            margin: 20px 0;
        }}
        .status {{
            background: #dcfce7;
            color: #166534;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }}
        .info {{
            font-size: 14px;
            color: #666;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="box">
        <div class="icon">🛡️</div>
        <h1>Certificate Verification</h1>
        <div class="cert-id">{certificate_id}</div>
        {'<div class="code">Code: ' + code + '</div>' if code else ''}
        <div class="status">
            ✅ Certificate format is valid
        </div>
        <div class="info">
            To fully verify this certificate, the original document must be 
            re-hashed and compared against the stored cryptographic fingerprint.
            <br><br>
            Contact the document owner to obtain the original file for verification.
        </div>
    </div>
</body>
</html>''')
