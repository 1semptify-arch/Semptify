# Semptify System Contracts

This document defines the formal contracts for all core systems in Semptify. Each contract specifies:

- **Purpose**: What the system does
- **Inputs**: What data it requires
- **Outputs**: What data it produces
- **Invariants**: Guarantees the system makes
- **Error Handling**: How failures are handled
- **Dependencies**: What other systems it depends on

---

## OAuth Contract

### Purpose

Authenticate a user with a cloud storage provider (Google Drive, Dropbox, OneDrive) and exchange an authorization code for access/refresh tokens.

### Inputs

- `provider`: Storage provider name (`google_drive`, `dropbox`, `onedrive`)
- `role`: User role (`tenant`, `advocate`, `legal`, `admin`, `manager`, `user`)
- `callback_url`: Full URL where the provider redirects after user authorization
- `code`: Authorization code returned by the provider (callback only)
- `state`: CSRF-safe state token created during initiation

### Outputs

- `user_id`: Unique, HMAC-signed user ID in format `{provider}_{role}_{unique_id}`
- `access_token`: Short-lived token for API calls
- `refresh_token`: Long-lived token for refreshing access
- `token_expires_at`: When the access token expires
- `provider_subject`: Provider's unique identifier for the user

### Invariants

1. **State Token**: Single-use, expires in 15 minutes, stored in DB
2. **User ID**: Always contains provider code and role, is HMAC-signed
3. **Token Storage**: Access token cached in memory (token_manager), refresh token persisted in DB
4. **Gate Marking**: `storage_connected` gate is marked ONLY after successful token exchange
5. **Security**: All token exchange uses HTTPS, state prevents CSRF

### Error Handling

- `ValueError`: Invalid or expired state token → restart OAuth flow
- `RuntimeError`: Token exchange failed → show error, restart OAuth flow
- `RuntimeError`: Identity verification failed → show error, restart OAuth flow

### Dependencies

- `OAuthState` model (DB)
- `token_manager` (in-memory cache)
- `generate_user_id()` (user_id module)
- `mark_gate()` (gates module)

### Implementation Location

- `app/modules/onboarding/oauth.py` (onboarding OAuth only)
- `app/modules/storage/router.py` (reconnect OAuth - TODO: unify)

---

## Storage Contract

### Purpose

Validate that a user has an active, working connection to their cloud storage provider and provide access to their tokens.

### Inputs

- `user_id`: Signed user ID to look up
- `provider`: Optional provider hint (parsed from user_id if not provided)

### Outputs

- `is_valid`: Boolean indicating if storage connection is active
- `access_token`: Current valid access token
- `provider`: Confirmed provider name
- `token_expires_at`: When the current token expires

### Invariants

1. **Token Freshness**: Access tokens are refreshed before they expire (5-minute buffer)
2. **Provider Detection**: Provider code is always embedded in user_id format
3. **Gate Enforcement**: `storage_connected` gate must be true for protected pages
4. **Session Persistence**: Tokens persist across sessions via refresh token in DB

### Error Handling

- `TokenExpiredError`: Refresh token invalid or expired → require full reconnect
- `ProviderUnavailableError`: Provider API down → retry with backoff
- `InvalidUserError`: User not found in DB → send to onboarding

### Dependencies

- `token_manager` (in-memory cache)
- `User` model (DB - stores refresh_token)
- `oauth_token_manager` (refresh logic)
- `parse_user_id()` (user_id module)

### Implementation Location

- `app/core/oauth_token_manager.py` (token refresh logic)
- `app/core/storage_middleware.py` (gate enforcement)
- `app/services/storage/` (provider-specific operations)

---

## Vault Contract

### Purpose

Create the canonical Semptify folder structure in the user's cloud storage and mark the vault as initialized.

### Inputs

- `user_id`: Signed user ID
- `provider`: Storage provider name
- `access_token`: Valid access token for the provider
- `role`: User role (determines which folders to create)

### Outputs

- `vault_initialized`: Boolean indicating all folders created successfully
- `folder_results`: Dict mapping folder name → creation status (success/failed)
- `errors`: List of any failures during folder creation

### Invariants

1. **Folder Structure**: Canonical paths defined in `app/core/vault_paths.py`
2. **Gate Marking**: `vault_initialized` gate marked ONLY if all folders created
3. **Role-Specific**: Different roles get different folder sets
4. **Idempotent**: Running vault install multiple times is safe (no duplicates)
5. **Verification**: Each folder is verified to exist and be accessible

### Error Handling

- `VaultFolderError`: Folder creation failed → log error, continue with remaining folders
- `VaultTokenError`: Token invalid during install → fail fast, require reconnect
- `VaultProviderError`: Provider API error → retry with backoff

### Dependencies

- `app/core/vault_paths.py` (canonical folder definitions)
- `app/modules/vault_installer/installer.py` (installation logic)
- `mark_gate()` (gates module)
- `token_manager` (for API access)

### Implementation Location

- `app/modules/vault_installer/installer.py` (main install logic)
- `app/sdk/vault/client.py` (reusable vault SDK)

---

## Reconnect Contract

### Purpose

Silently refresh an expired access token for a returning user without requiring full re-authorization.

### Inputs

- `user_id`: Signed user ID (contains provider and role)
- `refresh_token`: Long-lived refresh token from DB

### Outputs

- `access_token`: New valid access token
- `token_expires_at`: When the new token expires
- `success`: Boolean indicating if refresh succeeded

### Invariants

1. **Minimal Interaction**: User sees NO UI if refresh succeeds (silent background refresh)
2. **Fallback to Full Reauth**: If refresh fails, redirect to provider OAuth flow
3. **Session Preservation**: User's current page and state preserved during refresh
4. **Retry Logic**: Up to 3 refresh attempts with 60-second cooldown
5. **Token Update**: New tokens stored in both DB (refresh) and memory (access)

### Error Handling

- `RefreshTokenInvalidError`: Refresh token revoked/expired → full reauth required
- `ProviderUnavailableError`: Provider API down → show "service unavailable" message
- `NetworkError`: Temporary network issue → retry silently

### Dependencies

- `User` model (DB - stores refresh_token)
- `oauth_token_manager` (refresh logic)
- `token_manager` (cache new access token)

### Implementation Location

- `app/modules/storage/router.py` (current reconnect logic - needs simplification)
- `app/core/oauth_token_manager.py` (refresh mechanism)

### Current State

Reconnect exists but requires explicit user action. Goal: **silent background refresh** on any protected page access.

---

## Preamble Contract

### Purpose

The single entry point for all users. Determines where to route the user based on their authentication state and onboarding gate status.

### Inputs

- `request`: FastAPI Request object (contains cookies, headers)
- `user_id_cookie`: Optional signed user ID from cookie

### Outputs

- `redirect_path`: The next path the user should visit

### Invariants

1. **No Cookie = New User**: Always route to role selection
2. **Invalid Cookie = Stale**: Clear cookie, route to role selection
3. **Fully Onboarded = Returning User**: Route to role-specific home
4. **Partially Onboarded = Incomplete**: Route to exact next required step
5. **Single Entry Point**: All user routing happens here, nowhere else

### Decision Tree

```text
no cookie?
  → YES: /onboarding/select-role.html
  → NO: validate cookie signature
      invalid?
        → YES: clear cookie, /onboarding/select-role.html
        → NO: read gate state from DB
            storage_connected AND vault_initialized?
              → YES: route_user(user_id) → /tenant/home or /advocate/home
              → NO: next_required_path → /onboarding/providers or /onboarding/vault-setup
```

### Dependencies

- `verify_user_id()` (cookie_auth module)
- `get_onboarding_state()` (onboarding_state module)
- `route_user()` (workflow_engine module)
- `navigation.get_stage()` (navigation module)

### Implementation Location

- `app/modules/preamble/router.py`

---

## Welcome Contract

### Purpose

The public landing page that introduces Semptify and provides a call-to-action to start onboarding.

### Inputs

- `request`: FastAPI Request object

### Outputs

- `HTMLResponse`: Rendered welcome page with value proposition and CTA

### Invariants

1. **No Authentication Required**: Public page, accessible to anyone
2. **Single CTA**: One clear "Get Started" button pointing to `/preamble`
3. **Value Prop Clear**: Explains what Semptify does for tenants
4. **Privacy First**: No tracking, no analytics, no dark patterns

### Dependencies

- `navigation.get_onboarding_start()` (for CTA link)
- Static template: `static/public/welcome.html`

### Implementation Location

- `app/routers/welcome.py` (or served as static file)

---

## Document Upload Contract (Future)

### Purpose

Allow users to upload documents to their vault with automatic classification and indexing.

### Inputs

- `file`: Uploaded file (multipart/form-data)
- `user_id`: Signed user ID from cookie
- `folder_path`: Optional target folder (defaults to root)

### Outputs

- `document_id`: Unique identifier for the uploaded document
- `storage_path`: Full path where file was stored
- `classification`: Document type (lease, notice, receipt, etc.)
- `indexed`: Boolean indicating if document was added to search index

### Invariants

1. **Storage Required**: User must have `storage_connected` and `vault_initialized` gates
2. **Path Validation**: All uploads go to canonical vault folders only
3. **File Size Limits**: Enforce maximum file size (e.g., 50MB)
4. **Virus Scanning**: Scan uploaded files before storage
5. **Deduplication**: Don't upload duplicate files (hash check)

### Error Handling

- `StorageNotConnectedError`: Redirect to onboarding
- `VaultNotInitializedError**: Redirect to vault setup
- `FileTooLargeError`: Show error, reject upload
- `UnsupportedFileTypeError`: Show error, reject upload

### Dependencies

- `storage_middleware` (gate enforcement)
- `vault_installer` (folder validation)
- `document_classifier` (auto-classification)
- `search_indexer` (indexing)

### Implementation Location

- `app/routers/documents.py` (upload endpoint)
- `app/services/document_processor.py` (classification/indexing)

---

## Contract Enforcement

All contracts are enforced through:

1. **Type hints**: Python type annotations on all function signatures
2. **Validation**: Input validation at function entry
3. **Error types**: Specific exception types for each failure mode
4. **Logging**: Detailed logs for debugging and audit
5. **Tests**: Contract tests verify invariants are maintained

### Contract Test Pattern

```python
async def test_oauth_contract():
    # Given: valid inputs
    provider = "google_drive"
    role = "tenant"
    callback_url = "https://semptify.org/onboarding/callback/google_drive"
    
    # When: initiate OAuth
    state = await create_oauth_state(db, provider, role, callback_url)
    
    # Then: invariants hold
    assert len(state) == 43  # token_urlsafe(32) produces 43 chars
    assert state not in [existing_states]  # unique
    # ... more invariants
```
