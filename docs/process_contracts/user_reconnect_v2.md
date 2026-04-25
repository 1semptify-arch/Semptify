# Process Contract: User Reconnect Flow

**Contract ID**: `proc_user_reconnect`  
**Function Group**: `user_session_recovery`  
**Version**: 2.0  
**Status**: Active  
**Created**: 2026-04-24

---

## 1. Process Overview

**Purpose**: Enable **returning users** to reconnect their Semptify session. This is exclusively for users who have used Semptify before.

**Trigger**: User visits `/storage/` with or without a valid `semptify_uid` cookie.

**Success Outcome**: User's session restored via `provider_subject` lookup, redirected to their role-appropriate dashboard.

**Single Source of Truth**: The OAuth `provider_subject` (Google/Dropbox/Microsoft user ID) is the canonical identity.

---

## 2. Entry Criteria

| Condition | Required | Source |
|-----------|----------|--------|
| User has previously used Semptify | Yes | Determined by `provider_subject` match in DB |
| User has valid cookie OR needs re-auth | No | Handled transparently |
| User's storage provider is known | Yes | From cookie or user selection at `/storage/reconnect` |

**Entry Points**:
- `/storage/` - User with cookie (most common)
- `/storage/reconnect` - User lost cookie, must select provider

---

## 3. Process Steps

### Flow A: Returning User with Valid Session
```
GET /storage/
  ↓
storage_home() parses semptify_uid=GU7x9kM2pQ
  ↓
provider=google_drive, role=tenant extracted via parse_user_id()
  ↓
get_valid_session(auto_refresh=True) returns valid session
  ↓
_route_user(user_id) → /tenant/documents
  ↓
Redirect to tenant dashboard
```

### Flow B: Returning User with Expired Tokens (Silent Reauthorize)
```
GET /storage/
  ↓
storage_home() parses cookie
  ↓
get_valid_session() detects expired token
  ↓
refresh_access_token() succeeds with provider
  ↓
Session renewed in DB
  ↓
_route_user(user_id) → home page
```

### Flow C: Returning User with Invalid Session (Silent Reauthorize)
```
GET /storage/
  ↓
storage_home() parses cookie → GU7x9kM2pQ
  ↓
get_valid_session() returns None (refresh failed)
  ↓
Provider extracted: google_drive
  ↓
Redirect to /storage/auth/google_drive?existing_uid=GU7x9kM2pQ
  ↓
initiate_oauth() detects returning user, extracts role from user ID
  ↓
OAuth state created with role=tenant
  ↓
User authenticates with Google
  ↓
oauth_callback() matches user by provider_subject lookup
  ↓
Existing user_id confirmed, new tokens issued
  ↓
_route_user(user_id) → home page
```

### Flow D: Reconnect User (Lost Cookie)
```
GET /storage/reconnect
  ↓
User selects their storage provider (Google Drive/Dropbox/OneDrive)
  ↓
Redirect to /storage/auth/google_drive?return_to=/storage/reconnect
  ↓
initiate_oauth() (no existing_uid cookie = reconnection attempt)
  ↓
OAuth state created with default role=tenant
  ↓
User authenticates with Google
  ↓
oauth_callback() calls get_user_by_provider_subject(db, "google_drive", provider_subject)
  ↓
MATCH FOUND → User exists in DB
  ↓
Existing user_id returned (e.g., GU7x9kM2pQ)
  ↓
New tokens saved, cookie set
  ↓
_route_user(user_id) → home page
```

---

## 4. Exit Criteria

| Condition | Required | Verification |
|-----------|----------|--------------|
| `semptify_uid` cookie set | Yes | Browser cookie with 1-year expiry |
| Storage tokens valid | Yes | `get_valid_session()` confirms |
| User identity verified | Yes | `provider_subject` matched in DB |
| User redirected to role dashboard | Yes | `route_user()` determines target |

---

## 5. Error Handling

| Scenario | Action | User Message |
|----------|--------|--------------|
| Invalid user ID in cookie | Clear cookie, redirect to /storage/reconnect | "Please reconnect your storage" |
| Token refresh failed | Silent OAuth reauthorize | Brief OAuth screen only |
| Provider mismatch in user ID | 400 error | "Provider mismatch" (security) |
| Identity mismatch (wrong OAuth account) | 403 error | "Please sign in with your originally linked storage account" |
| No matching user found (new user at reconnect page) | Offer to start onboarding | "No Semptify data found. Start fresh?" |

---

## 6. User Experience

**Tone**: Invisible/reassuring - "Reconnecting you..."

**Flow Characteristics**:
- **Flow A** (< 100ms): Instant redirect, user sees nothing
- **Flow B** (< 2s): Silent token refresh, user sees brief spinner
- **Flow C** (5-15s): OAuth reauthorize, user sees provider login briefly
- **Flow D** (5-15s): Provider selection → OAuth match → home

**Critical UX Principle**: Users with valid cookies **never select provider or role again**. Provider and role are extracted from user ID. The system remembers.

---

## 7. Security Considerations

- **Identity Verification**: `provider_subject` is the only source of truth
- **Cookie Binding**: `existing_uid` param must match cookie to prevent UID swapping
- **Provider Mismatch Guard**: User ID provider char must match OAuth provider
- **Token Encryption**: All tokens AES-256-GCM encrypted at rest
- **State CSRF**: OAuth state token single-use, 15-minute expiry

---

## 8. Implementation Files

| File | Purpose |
|------|---------|
| `app/routers/storage.py` | Main entry point, OAuth handlers, session management |
| `app/core/user_id.py` | User ID generation/parsing |
| `app/core/user_context.py` | UserRole enum, permissions |
| `app/core/workflow_engine.py` | `route_user()` - SSOT for routing |
| `static/reconnect/index.html` | Reconnect UI for lost-cookie users |

---

## 9. API Endpoints

### GET `/storage/`
**Purpose**: Main entry point for returning users  
**Cookie**: `semptify_uid`  
**Response**: 302 redirect to home page, OAuth, or /storage/reconnect

### GET `/storage/session/status`
**Purpose**: Check session status for frontend auto-reconnect  
**Response**: `{has_session, is_valid, user_id, role, provider, has_storage}`

### GET `/storage/reconnect`
**Purpose**: UI for users who lost their cookie  
**Response**: HTML page with provider selection

### GET `/storage/auth/{provider}`
**Query**: `?existing_uid={uid}&return_to={url}`  
**Purpose**: Initiate OAuth flow for reconnect  
**Logic**: If `existing_uid` → returning user reauth; else → reconnection attempt

### GET `/storage/callback/{provider}`
**Query**: `?code={auth_code}&state={csrf_token}`  
**Purpose**: OAuth callback, identify user by `provider_subject`  
**Response**: Redirect to role-appropriate dashboard

---

**END OF CONTRACT**
