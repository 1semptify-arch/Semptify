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
| ----------- | ---------- | -------- |
| User has previously used Semptify | Yes | Determined by `provider_subject` match in DB |
| User has valid cookie OR needs re-auth | No | Handled transparently |
| User's storage provider is known | Yes | From cookie or user selection at `/storage/reconnect` |

**Entry Points**:

- `/storage/` - User with cookie (most common)
- `/storage/reconnect` - User lost cookie, must select provider

---

## 3. Process Steps

### Flow A: Returning User with Valid Session

```text
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

```text
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

```text
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

```text
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
| ----------- | ---------- | -------------- |
| `semptify_uid` cookie set | Yes | Browser cookie with 1-year expiry |
| Storage tokens valid | Yes | `get_valid_session()` confirms |
| User identity verified | Yes | `provider_subject` matched in DB |
| User redirected to role dashboard | Yes | `route_user()` determines target |

---

## 5. Error Handling

| Scenario | Action | User Message |
| ---------- | -------- | -------------- |
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

## 7a. Traffic-Light Verification Model (the "express lane")

Storage connection health is verified at three levels, matching how much risk
the requested action carries. This is the SSOT mechanism behind Flows A-D above
— it is what decides whether a user is waved straight through, silently
refreshed, or sent back through OAuth.

| Level | Ice-cube analogy | Token check | Used for |
| ------- | ------------------- | -------------- | ---------- |
| 🟢 **GREEN** | Ice cube, any age | Memory cache only, no provider call | Read-only: library, viewing documents/timeline |
| 🟡 **YELLOW** | Ice cube < 4hrs, not melted | Cache + auto-refresh via provider if expired | Default app use: uploads, vault writes, contacts |
| 🔴 **RED** | Fresh ice cube < 30min | Always asks provider live, no cache accepted | Destructive/high-risk: delete, court filings, exports |

Implemented as FastAPI dependencies in `app/core/security.py`:
`Depends(green_access)`, `Depends(yellow_access)`, `Depends(red_access)`.

**Identity check, not an accounts system**: the cookie holds a `semptify_uid`
that encodes role + chosen OAuth provider directly in the ID string — nothing
is looked up in a user table to know who someone is. Verification means
confirming the access token on file is still the valid other half of that
same OAuth connection (asking the provider), not authenticating against
stored credentials.

**No logging / no counting of users**: Semptify does not log reconnection
attempts, does not count users, and does not track individual sessions for
analytics. The user is not an "account" — they are allowing Semptify to
process and organize files they already own in their own storage. Verification
exists only to confirm the storage connection is live, never to record who
connected or how often.

---

## 8. Implementation Files

| File | Purpose |
| ------ | --------- |
| `app/modules/storage/router.py` | Main entry point (`/storage/`), OAuth handlers, session management, provider picker (`/storage/providers`), Rehome flow |
| `app/modules/onboarding/reconnect.py` | Owns `/storage/reconnect` (lost-cookie provider picker) as a gate-enforcement concern |
| `app/core/security.py` | Traffic-light access levels (`green_access`/`yellow_access`/`red_access`) — see Section 7a |
| `app/core/user_id.py` | User ID generation/parsing (encodes role + provider in the ID itself) |
| `app/core/user_context.py` | UserRole enum, permissions |
| `app/core/workflow_engine.py` | `route_user()` - SSOT for routing |

**Note**: `returning_user_contract.md` (v1.0, Draft) is superseded by this document and has been archived to `archive/obsolete-2026-06-29/` — it contradicted the no-logging principle below (it called for logging reconnection attempts) and pointed to a non-existent file path.

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

#### END OF CONTRACT
