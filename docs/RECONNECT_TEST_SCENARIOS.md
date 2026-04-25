# Reconnect Flow Test Scenarios

**Contract**: `proc_user_reconnect` (Returning User Reconnect)  
**Note**: This document covers **reconnect** for returning users only. Onboarding is a separate process with its own contract.

## Unified Reconnect Philosophy

**Per Builder's Bible**: The reconnect process handles:
- Returning user with valid cookie (session exists)
- Reconnect user who lost cookie (but has storage provider)

The **provider_subject** is the single source of truth. The system looks up the user by their OAuth identity, not by cookie.

---

## Test Scenario Matrix

### Scenario 1: Returning User - Valid Cookie + Valid Session
**Precondition:** User has `semptify_uid=GU7x9kM2pQ` cookie + valid DB session

**Flow:**
1. GET `/storage/`
2. `storage_home()` parses user ID → provider=google_drive, role=tenant
3. `get_valid_session()` returns valid session
4. `_route_user(semptify_uid)` → `/tenant/documents`
5. **Result:** User lands directly on their home page

**Expected:** 302 redirect to `/tenant/documents`

---

### Scenario 2: Returning User - Valid Cookie + Expired Session (Auto-Refresh)
**Precondition:** User has cookie + expired access token + valid refresh token

**Flow:**
1. GET `/storage/`
2. `storage_home()` calls `get_valid_session(auto_refresh=True)`
3. Token expired detected
4. `refresh_access_token()` succeeds with provider
5. Session updated in DB
6. `_route_user(semptify_uid)` → home page
7. **Result:** User lands on home page (refresh was invisible)

**Expected:** 302 redirect to `/tenant/documents`, session renewed

---

### Scenario 3: Returning User - Valid Cookie + Invalid Session (Silent Reauthorize)
**Precondition:** User has cookie + expired tokens + refresh failed

**Flow:**
1. GET `/storage/`
2. `storage_home()` calls `get_valid_session()` → returns None
3. Provider extracted from user ID: `parse_user_id("GU7x9kM2pQ")` → google_drive
4. Redirect to `/storage/auth/google_drive?existing_uid=GU7x9kM2pQ`
5. `initiate_oauth()` detects returning user from `existing_uid`
6. OAuth state created with role extracted from user ID
7. User authenticates with Google
8. `oauth_callback()` matches user by `provider_subject` lookup
9. User identity confirmed, new tokens issued
10. **Result:** User lands on home page, never asked for provider/role

**Expected:** 302 → OAuth → 302 → `/tenant/documents` (user sees only brief OAuth screen)

---

### Scenario 4: Reconnect User - Lost Cookie, Has Storage Provider
**Precondition:** No cookie, but user has Semptify data in their cloud storage

**Flow:**
1. User visits `/storage/reconnect`
2. Static page shows provider selection (Google Drive, Dropbox, OneDrive)
3. User selects their provider (e.g., Google Drive)
4. JavaScript redirects to `/storage/auth/google_drive?return_to=/storage/reconnect`
5. `initiate_oauth()` treats as new user (no existing_uid cookie)
6. OAuth state created with default role="tenant"
7. User authenticates with Google
8. `oauth_callback()` calls `get_user_by_provider_subject(db, "google_drive", provider_subject)`
9. **Match found** → User exists! Return existing user_id
10. New tokens saved, cookie set
11. **Result:** User recognized, lands on home page

**Expected:** Provider selection → OAuth → home page (user only selects provider once)

---

### Scenario 5: Session Status Check (API Endpoint)
**Precondition:** Frontend needs to check if user is logged in

**Flow:**
1. Frontend calls `GET /storage/session/status`
2. Cookie `semptify_session` validated
3. Returns: `{has_session: true, is_valid: true, user_id: "GU7x9kM2pQ", role: "tenant", provider: "google_drive"}`
4. **Result:** Frontend can auto-redirect to OAuth without asking provider

**Expected:** JSON response with session details for returning user auto-reconnect

---

## Key Architectural Points

### 1. Provider Identification via OAuth Subject
```python
# In oauth_callback() - line ~1609
matched_user = await get_user_by_provider_subject(db, provider, provider_subject)
```

This is the **single source of truth** for user identity. The `provider_subject` is the unique ID from Google/Dropbox/Microsoft that never changes.

### 2. User ID Cookie Format
```
Format: <provider_code><role_code><8_char_random>
Example: GU7x9kM2pQ
         ^ ^ ^^^^^^^^
         | |  random
         | role='tenant' (U maps to tenant)
         provider='google_drive' (G = Google Drive)
```

### 3. Role Canonical Mapping
- `UserRole.TENANT` = "tenant" (canonical)
- `UserRole.USER` = "user" (legacy alias)
- Both map to `RoleCode.USER` = "U" in user ID
- Both decode to "tenant" via `CODE_TO_ROLE`

### 4. Unified OAuth Entry Point
Both returning and new users go through:
```
/storage/auth/{provider}
```

The difference:
- **Returning user**: Has `existing_uid` param or cookie → role extracted from user ID
- **New user**: Has `role` param → role validated and used for new ID

### 5. Vault Path Determination
Once authenticated, the vault path is always:
```
/{provider}/Semptify5.0/Vault/  (e.g., /google_drive/Semptify5.0/Vault/)
```

The provider is extracted from the user ID (first char) and used to initialize the correct storage client.

---

## Test Commands

### Manual Test: Scenario 3 (Silent Reauthorize)
```bash
# 1. Clear session from DB (simulates expired tokens)
# 2. Keep cookie semptify_uid=GU7x9kM2pQ
# 3. Visit: http://localhost:8000/storage/
# Expected: Redirects to Google OAuth, then back to /tenant/documents
```

### Manual Test: Scenario 4 (Reconnect with Provider Subject Match)
```bash
# 1. Clear all cookies
# 2. Visit: http://localhost:8000/storage/reconnect
# 3. Select Google Drive
# Expected: OAuth flow, matched to existing user, home page
```

### API Test: Session Status
```bash
curl -b "semptify_session=<valid_token>" \
  http://localhost:8000/storage/session/status
```

---

## Error Scenarios

### Error 1: Provider Mismatch in User ID
**Precondition:** User ID is "GU7x9kM2pQ" but tries to OAuth with Dropbox

**Result:** 400 error "existing_uid provider mismatch for requested OAuth provider"

### Error 2: Invalid Role in State Data
**Precondition:** OAuth state has role="invalid_role"

**Result:** Falls back to "tenant" role in callback

### Error 3: Identity Mismatch (Security)
**Precondition:** User ID exists, but OAuth subject doesn't match stored subject

**Result:** 403 error "The connected storage account does not match this Semptify user"

---

## Compliance with Builder's Bible

✅ **Free Forever**: No payment gates in any flow  
✅ **No Ads**: No promotional content  
✅ **Privacy by Design**: User data never stored server-side  
✅ **Evidence Integrity**: Vault paths deterministic and auditable  
✅ **Calm UX**: Returning users never asked for information they already provided  
✅ **Single Source of Truth**: `route_user()` and `provider_subject` lookup  
✅ **Stateless**: No server-side session state beyond encrypted tokens  
