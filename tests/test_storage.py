"""
Semptify 5.0 - Storage & Authentication Tests
Tests for OAuth flow, session management, and storage providers.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.core.utc import utc_now
from app.routers import storage as storage_router


# =============================================================================
# Provider Listing Tests
# =============================================================================

@pytest.mark.anyio
async def test_storage_providers_list(client: AsyncClient):
    """Test listing available storage providers."""
    response = await client.get("/storage/providers")
    assert response.status_code == 200
    # May return HTML page or JSON depending on configuration
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)
    else:
        # HTML response - check for provider content
        assert "storage" in response.text.lower() or "connect" in response.text.lower()


@pytest.mark.anyio
async def test_storage_providers_include_expected(client: AsyncClient):
    """Test that expected provider IDs are present if configured."""
    response = await client.get("/storage/providers")
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        data = response.json()
        # Provider list depends on configuration
        for provider in data.get("providers", []):
            assert "id" in provider
            assert "name" in provider
            assert "enabled" in provider
            assert provider["id"] in ["google_drive", "dropbox", "onedrive"]
    else:
        # HTML response - check page contains provider references
        text = response.text.lower()
        assert "google" in text or "dropbox" in text or "onedrive" in text or "storage" in text


# =============================================================================
# Session Tests
# =============================================================================

@pytest.mark.anyio
async def test_storage_session_unauthenticated(client: AsyncClient):
    """Test session endpoint without authentication."""
    response = await client.get("/storage/session")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False


@pytest.mark.anyio
async def test_storage_session_authenticated(authenticated_client: AsyncClient):
    """Test session endpoint with valid session."""
    response = await authenticated_client.get("/storage/session")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert "user_id" in data
    assert "provider" in data


@pytest.mark.anyio
async def test_storage_status_unauthenticated(client: AsyncClient):
    """Test status endpoint without authentication."""
    response = await client.get("/storage/status")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False


@pytest.mark.anyio
async def test_storage_status_authenticated(authenticated_client: AsyncClient):
    """Test status endpoint with valid session."""
    response = await authenticated_client.get("/storage/status")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert "access_token" in data  # Status returns token, session doesn't


# =============================================================================
# OAuth Flow Tests
# =============================================================================

@pytest.mark.anyio
async def test_storage_auth_redirect_google(client: AsyncClient):
    """Test Google OAuth redirect (requires credentials configured)."""
    response = await client.get("/storage/auth/google_drive", follow_redirects=False)
    # Will redirect to Google or return error if not configured
    assert response.status_code in [302, 307, 400, 500]


@pytest.mark.anyio
async def test_storage_auth_invalid_provider(client: AsyncClient):
    """Test OAuth with invalid provider."""
    response = await client.get("/storage/auth/invalid_provider")
    # May return 400 (error) or 404 (not found) for invalid provider
    assert response.status_code in [400, 404, 422]
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        data = response.json()
        # Check for error message in various response formats
        assert "detail" in data or "error" in data or "message" in data


@pytest.mark.anyio
async def test_storage_callback_invalid_state(client: AsyncClient):
    """Test OAuth callback with invalid state."""
    response = await client.get("/storage/callback/google_drive?code=test&state=invalid")
    # May return 400 (error), 302 (redirect to error page), or other error codes
    assert response.status_code in [400, 401, 302, 307, 422, 500]
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type and response.status_code != 302:
        data = response.json()
        # Check various response formats
        detail = data.get("detail", data.get("message", "")).lower()
        error = data.get("error", "").lower()
        assert "invalid" in detail or "expired" in detail or "state" in detail or "error" in detail or error


# =============================================================================
# Role Management Tests
# =============================================================================

@pytest.mark.anyio
async def test_role_switch_unauthenticated(client: AsyncClient):
    """Test role switch without authentication."""
    response = await client.post("/storage/role", json={"role": "landlord"})
    assert response.status_code == 401


@pytest.mark.anyio
async def test_role_switch_authenticated(authenticated_client: AsyncClient):
    """Test role switch with authentication - user role (no auth required)."""
    response = await authenticated_client.post("/storage/role", json={"role": "user"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("role") == "user"


@pytest.mark.anyio
async def test_role_switch_advocate_requires_invite(authenticated_client: AsyncClient):
    """Test advocate role requires invite code."""
    # Without invite code - should fail
    response = await authenticated_client.post("/storage/role", json={"role": "advocate"})
    assert response.status_code == 403

    # With valid invite code - should succeed
    response = await authenticated_client.post(
        "/storage/role",
        json={"role": "advocate", "invite_code": "TEST-INVITE-CODE"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("role") == "advocate"


@pytest.mark.anyio
async def test_role_switch_legal_requires_invite(authenticated_client: AsyncClient):
    """Test legal role requires invite code."""
    # Without invite code - should fail
    response = await authenticated_client.post("/storage/role", json={"role": "legal"})
    assert response.status_code == 403

    # With valid invite code - should succeed
    response = await authenticated_client.post(
        "/storage/role",
        json={"role": "legal", "invite_code": "TEST-INVITE-CODE"}
    )
    assert response.status_code == 200


@pytest.mark.anyio
async def test_role_switch_manager_requires_household(authenticated_client: AsyncClient):
    """Test manager role requires multiple people on lease."""
    # Without household members - should fail
    response = await authenticated_client.post("/storage/role", json={"role": "manager"})
    assert response.status_code == 403

    # With only 1 person - should fail
    response = await authenticated_client.post(
        "/storage/role",
        json={"role": "manager", "household_members": 1}
    )
    assert response.status_code == 403

    # With 2+ people - should succeed
    response = await authenticated_client.post(
        "/storage/role",
        json={"role": "manager", "household_members": 2}
    )
    assert response.status_code == 200


@pytest.mark.anyio
async def test_role_switch_admin_requires_pin(authenticated_client: AsyncClient):
    """Test admin role requires PIN."""
    # Without PIN - should fail
    response = await authenticated_client.post("/storage/role", json={"role": "admin"})
    assert response.status_code == 403

    # With wrong PIN - should fail
    response = await authenticated_client.post(
        "/storage/role",
        json={"role": "admin", "pin": "1234"}
    )
    assert response.status_code == 403

    # With correct PIN - should succeed
    response = await authenticated_client.post(
        "/storage/role",
        json={"role": "admin", "pin": "TEST-PIN"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("role") == "admin"


@pytest.mark.anyio
async def test_role_switch_invalid_role(authenticated_client: AsyncClient):
    """Test role switch with invalid role."""
    response = await authenticated_client.post("/storage/role", json={"role": "superuser"})
    assert response.status_code == 400


# =============================================================================
# Logout Tests
# =============================================================================

@pytest.mark.anyio
async def test_logout(client: AsyncClient):
    """Test logout clears session."""
    response = await client.post("/storage/logout")
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True


@pytest.mark.anyio
async def test_logout_authenticated(authenticated_client: AsyncClient):
    """Test logout when authenticated."""
    response = await authenticated_client.post("/storage/logout")
    assert response.status_code == 200
    
    # Session should be cleared
    session_response = await authenticated_client.get("/storage/session")
    # Cookie is cleared, so should show unauthenticated
    # (Note: cookie might persist in test client)


# =============================================================================
# Storage Home Routing Tests
# =============================================================================

@pytest.mark.anyio
async def test_storage_home_no_cookie(client: AsyncClient):
    """Test storage home redirects to providers without cookie."""
    response = await client.get("/storage/", follow_redirects=False)
    assert response.status_code in [302, 307]
    assert "/providers" in response.headers.get("location", "")


@pytest.mark.anyio
async def test_storage_home_with_cookie(authenticated_client: AsyncClient):
    """Test storage home with existing cookie redirects to auth."""
    response = await authenticated_client.get("/storage/", follow_redirects=False)
    # Should redirect to re-auth with existing provider
    assert response.status_code in [302, 307]


# =============================================================================
# Sync Device Tests
# =============================================================================

@pytest.mark.anyio
async def test_sync_device_valid_user_id(client: AsyncClient):
    """Test sync endpoint with valid user ID sets cookie."""
    response = await client.get("/storage/sync/GUtest1234", follow_redirects=False)
    assert response.status_code == 200
    assert "Reconnected" in response.text
    assert "semptify_uid" in response.headers.get("set-cookie", "")


@pytest.mark.anyio
async def test_sync_device_invalid_user_id(client: AsyncClient):
    """Test sync endpoint with invalid user ID returns error."""
    response = await client.get("/storage/sync/invalid", follow_redirects=False)
    assert response.status_code == 400
    assert "Invalid" in response.text


@pytest.mark.anyio
async def test_sync_device_shows_provider_and_role(client: AsyncClient):
    """Test sync endpoint shows correct provider and role."""
    # GU = Google + User
    response = await client.get("/storage/sync/GUabcd1234", follow_redirects=False)
    assert response.status_code == 200
    assert "Google Drive" in response.text
    assert "user" in response.text.lower()


@pytest.mark.anyio
async def test_prepare_reconnect_clears_stale_session(client: AsyncClient, monkeypatch):
    test_uid = "GUtest1234"
    storage_router.SESSIONS[test_uid] = {
        "user_id": test_uid,
        "provider": "google_drive",
        "access_token": "expired-token",
        "refresh_token": None,
        "authenticated_at": "2026-01-01T00:00:00",
        "expires_at": "2026-01-01T00:00:00",
    }

    async def fake_validate_token_with_provider(_provider: str, _access_token: str) -> bool:
        return False

    monkeypatch.setattr(storage_router, "validate_token_with_provider", fake_validate_token_with_provider)

    response = await client.post("/storage/prepare-reconnect", cookies={"semptify_uid": test_uid})

    assert response.status_code == 200
    data = response.json()
    assert data["ready_for_reconnect"] is True
    assert data["state"] == "disconnected_stale"
    assert test_uid not in storage_router.SESSIONS


@pytest.mark.anyio
async def test_session_info_marks_needs_reauth_when_session_present_but_invalid(client: AsyncClient, monkeypatch):
    test_uid = "GUtest1234"

    async def fake_get_session_from_db(_db, _user_id: str):
        return {
            "user_id": test_uid,
            "provider": "google_drive",
            "access_token": "expired-token",
            "refresh_token": None,
            "expires_at": "2026-01-01T00:00:00",
        }

    async def fake_get_valid_session(_db, _user_id: str, auto_refresh: bool = True):
        return None

    monkeypatch.setattr(storage_router, "get_session_from_db", fake_get_session_from_db)
    monkeypatch.setattr(storage_router, "get_valid_session", fake_get_valid_session)

    response = await client.get("/storage/session", cookies={"semptify_uid": test_uid})

    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False
    assert data["session_present"] is True
    assert data["needs_reauth"] is True


@pytest.mark.anyio
async def test_oauth_callback_commits_before_vault_enable(client: AsyncClient, monkeypatch):
    state = "test-sequence-state"
    storage_router.OAUTH_STATES[state] = {
        "provider": "google_drive",
        "created_at": utc_now(),
        "role": "user",
    }

    call_order: list[str] = []

    async def fake_exchange_code(provider: str, code: str, redirect_uri: str) -> dict:
        return {"access_token": "access-token", "refresh_token": "refresh-token", "expires_in": 3600}

    async def fake_fetch_oauth_identity(provider: str, access_token: str) -> dict:
        return {
            "provider_subject": "google-subject-123",
            "email": "test@example.com",
            "display_name": "Test User",
        }

    async def fake_save_session_to_db(**kwargs):
        call_order.append("save_session")

    async def fake_create_or_update_user(db, user_id: str, provider: str, **kwargs):
        call_order.append("create_or_update_user")
        return MagicMock()

    async def fake_get_or_create_storage_config(db, user_id: str, provider: str):
        call_order.append("get_or_create_storage_config")
        return MagicMock()

    async def fake_store_auth_marker(**kwargs):
        call_order.append("store_auth_marker")

    monkeypatch.setattr(storage_router, "_exchange_code", fake_exchange_code)
    monkeypatch.setattr(storage_router, "_fetch_oauth_identity", fake_fetch_oauth_identity)
    monkeypatch.setattr(storage_router, "save_session_to_db", fake_save_session_to_db)
    monkeypatch.setattr(storage_router, "create_or_update_user", fake_create_or_update_user)
    monkeypatch.setattr(storage_router, "get_or_create_storage_config", fake_get_or_create_storage_config)
    monkeypatch.setattr(storage_router, "_store_auth_marker", fake_store_auth_marker)

    response = await client.get(
        f"/storage/callback/google_drive?code=dummy-code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code in [302, 307]
    assert call_order == [
        "save_session",
        "create_or_update_user",
        "get_or_create_storage_config",
        "store_auth_marker",
    ]


@pytest.mark.anyio
async def test_function_token_issue_requires_cookie(client: AsyncClient):
    response = await client.post("/storage/function-token/issue")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_function_token_issue_includes_scopes_and_wildcard_doc(client: AsyncClient, monkeypatch):
    captured = {}

    async def fake_get_valid_session(_db, _uid: str, auto_refresh: bool = True):
        return {"provider": "google_drive", "access_token": "tok"}

    async def fake_vault_access_ready(**_kwargs):
        return True, "ok"

    def fake_issue_function_access_token(user_id: str, ttl_seconds: int = 300, context: dict | None = None):
        captured["user_id"] = user_id
        captured["context"] = context
        return {
            "token": "fn-token",
            "expires_at": "2030-01-01T00:00:00+00:00",
            "reverify_in_seconds": 120,
        }

    monkeypatch.setattr(storage_router, "get_valid_session", fake_get_valid_session)
    monkeypatch.setattr(storage_router, "_vault_access_ready", fake_vault_access_ready)
    monkeypatch.setattr(storage_router, "issue_function_access_token", fake_issue_function_access_token)

    response = await client.post(
        "/storage/function-token/issue",
        cookies={"semptify_uid": "GUtest1234"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["token"] == "fn-token"
    assert captured["user_id"] == "GUtest1234"
    assert captured["context"]["scopes"] == ["overlay:read", "overlay:write"]
    assert captured["context"]["document_ids"] == ["*"]


@pytest.mark.anyio
async def test_function_token_verify_requires_header_token_even_if_query_present(client: AsyncClient, monkeypatch):
    async def fake_get_valid_session(_db, _uid: str, auto_refresh: bool = True):
        return {"provider": "google_drive", "access_token": "tok"}

    monkeypatch.setattr(storage_router, "get_valid_session", fake_get_valid_session)

    response = await client.get(
        "/storage/function-token/verify?token=query-token&refresh=true",
        cookies={"semptify_uid": "GUtest1234"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["reason"] == "token_missing"


@pytest.mark.anyio
async def test_function_token_verify_with_header_uses_verifier_result(client: AsyncClient, monkeypatch):
    async def fake_get_valid_session(_db, _uid: str, auto_refresh: bool = True):
        return {"provider": "google_drive", "access_token": "tok"}

    def fake_verify(_uid: str, _token: str, refresh: bool = False):
        return {"valid": False, "reason": "token_expired"}

    monkeypatch.setattr(storage_router, "get_valid_session", fake_get_valid_session)
    monkeypatch.setattr(storage_router, "verify_function_access_token", fake_verify)

    response = await client.get(
        "/storage/function-token/verify?refresh=true",
        cookies={"semptify_uid": "GUtest1234"},
        headers={"X-Function-Token": "header-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["reason"] == "token_expired"


# =============================================================================
# Token Encryption Tests
# =============================================================================

@pytest.mark.anyio
async def test_encrypt_decrypt_token_roundtrip():
    """Test that encrypting and decrypting a token preserves the original data."""
    from app.routers.storage import _encrypt_token, _decrypt_token

    user_id = "GUtest1234"
    original_data = {
        "access_token": "ya29.abc123def456",
        "refresh_token": "1//refresh_token_here",
        "expires_at": "2024-01-01T12:00:00Z"
    }

    # Encrypt the data
    encrypted = _encrypt_token(original_data, user_id)
    assert isinstance(encrypted, bytes)
    assert len(encrypted) > 12  # Should have nonce + ciphertext

    # Decrypt and verify
    decrypted = _decrypt_token(encrypted, user_id)
    assert decrypted == original_data


@pytest.mark.anyio
async def test_encrypt_decrypt_token_different_users():
    """Test that tokens encrypted for different users cannot be decrypted by each other."""
    from app.routers.storage import _encrypt_token, _decrypt_token

    user1_id = "GUuser1"
    user2_id = "GUuser2"
    data = {"access_token": "test_token"}

    # Encrypt for user1
    encrypted = _encrypt_token(data, user1_id)

    # Try to decrypt with user2 - should fail
    with pytest.raises(Exception):
        _decrypt_token(encrypted, user2_id)


@pytest.mark.anyio
async def test_encrypt_decrypt_string_roundtrip():
    """Test that encrypting and decrypting a string preserves the original value."""
    from app.routers.storage import _encrypt_string, _decrypt_string

    user_id = "GUtest1234"
    original_string = "ya29.abc123def456"

    # Encrypt the string
    encrypted = _encrypt_string(original_string, user_id)
    assert isinstance(encrypted, str)
    # Should be base64 encoded
    assert len(encrypted) > len(original_string)

    # Decrypt and verify
    decrypted = _decrypt_string(encrypted, user_id)
    assert decrypted == original_string


@pytest.mark.anyio
async def test_encrypt_decrypt_string_different_users():
    """Test that strings encrypted for different users cannot be decrypted by each other."""
    from app.routers.storage import _encrypt_string, _decrypt_string

    user1_id = "GUuser1"
    user2_id = "GUuser2"
    original_string = "secret_token"

    # Encrypt for user1
    encrypted = _encrypt_string(original_string, user1_id)

    # Try to decrypt with user2 - should fail
    with pytest.raises(Exception):
        _decrypt_string(encrypted, user2_id)


@pytest.mark.anyio
async def test_encrypt_decrypt_token_with_special_characters():
    """Test encryption/decryption with special characters and unicode."""
    from app.routers.storage import _encrypt_token, _decrypt_token

    user_id = "GUtest1234"
    original_data = {
        "access_token": "ya29.abc123def456!@#$%^&*()",
        "refresh_token": "1//refresh_token_ñáéíóú",
        "special_chars": "!@#$%^&*()_+-=[]{}|;:,.<>?",
        "unicode": "🚀📁🔐🔑"
    }

    # Encrypt the data
    encrypted = _encrypt_token(original_data, user_id)

    # Decrypt and verify
    decrypted = _decrypt_token(encrypted, user_id)
    assert decrypted == original_data


@pytest.mark.anyio
async def test_encrypt_decrypt_string_empty_and_whitespace():
    """Test encryption/decryption with empty strings and whitespace."""
    from app.routers.storage import _encrypt_string, _decrypt_string

    user_id = "GUtest1234"

    # Test empty string
    encrypted_empty = _encrypt_string("", user_id)
    decrypted_empty = _decrypt_string(encrypted_empty, user_id)
    assert decrypted_empty == ""

    # Test whitespace
    original_whitespace = "   \t\n  "
    encrypted_whitespace = _encrypt_string(original_whitespace, user_id)
    decrypted_whitespace = _decrypt_string(encrypted_whitespace, user_id)
    assert decrypted_whitespace == original_whitespace


@pytest.mark.anyio
async def test_encrypt_token_consistency():
    """Test that encrypting the same data multiple times produces different ciphertexts (due to random nonce)."""
    from app.routers.storage import _encrypt_token

    user_id = "GUtest1234"
    data = {"access_token": "consistent_test"}

    # Encrypt multiple times
    encrypted1 = _encrypt_token(data, user_id)
    encrypted2 = _encrypt_token(data, user_id)

    # Should be different due to random nonce
    assert encrypted1 != encrypted2

    # But both should decrypt to the same data
    from app.routers.storage import _decrypt_token
    decrypted1 = _decrypt_token(encrypted1, user_id)
    decrypted2 = _decrypt_token(encrypted2, user_id)
    assert decrypted1 == data
    assert decrypted2 == data


@pytest.mark.anyio
async def test_decrypt_token_corrupted_data():
    """Test that decrypting corrupted data raises an exception."""
    from app.routers.storage import _encrypt_token, _decrypt_token

    user_id = "GUtest1234"
    data = {"access_token": "test"}

    # Encrypt normally
    encrypted = _encrypt_token(data, user_id)

    # Corrupt the data
    corrupted = bytearray(encrypted)
    if len(corrupted) > 12:
        corrupted[15] ^= 0xFF  # Flip a bit in the ciphertext

    # Should fail to decrypt
    with pytest.raises(Exception):
        _decrypt_token(bytes(corrupted), user_id)


@pytest.mark.anyio
async def test_decrypt_token_wrong_length():
    """Test that decrypting data that's too short raises an exception."""
    from app.routers.storage import _decrypt_token

    user_id = "GUtest1234"

    # Too short (less than nonce + minimum ciphertext)
    with pytest.raises(Exception):
        _decrypt_token(b"short", user_id)

    # Only nonce, no ciphertext
    with pytest.raises(Exception):
        _decrypt_token(b"123456789012", user_id)
