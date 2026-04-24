# Process Contract: Returning User Reconnect

**Contract ID**: `proc_returning_user_reconnect`  
**Function Group**: `user_session_recovery`  
**Version**: 1.0  
**Status**: Draft  
**Created**: 2026-04-23

---

## 1. Process Overview

**Purpose**: Enable returning users to reconnect their Semptify session when they click "Returning User" from the welcome page.

**Trigger**: User clicks "Returning User" button on `welcome.html`

**Success Outcome**: User's session restored, redirected to their role-appropriate dashboard with full vault access.

---

## 2. Entry Criteria

| Condition | Required | Source |
|-----------|----------|--------|
| User arrives from welcome page | Yes | Referrer or session flag |
| User has existing Semptify journal | Yes | OAuth provider identity |
| User's storage was previously connected | Yes | OAuth tokens exist in DB |

**CRITICAL**: Semptify has NO accounts. Identity is storage-based only. No personal data tracked.

---

## 3. Process Steps

### Step 1: Provider Selection
**Screen**: `/storage/reconnect` (`static/reconnect/index.html`)

**Input**: User picks their storage provider (Google Drive/Dropbox/OneDrive)

**Output**: OAuth flow initiated → provider identifies user by provider account ID → `user_id` resolved

### Step 2: Verify Journal Exists
**Backend Action**: Check if Semptify folder exists in user's storage

**Success**: Journal found → Proceed to Step 3  
**Failure**: No journal → Show "No journal found" → Option to start fresh onboarding

### Step 3: Verify Storage Connection
**Backend Action**: Check if OAuth tokens exist and are valid

**Case A - Tokens Valid**:  
→ Skip OAuth, restore session from DB tokens  
→ Redirect to dashboard

**Case B - Tokens Expired but Refreshable**:  
→ Use refresh token to get new access token  
→ Update DB, restore session  
→ Redirect to dashboard

**Case C - Tokens Revoked/Missing**:  
→ Save `return_to` in session  
→ Redirect to OAuth provider  
→ After OAuth callback → restore session → redirect to dashboard

### Step 4: Session Restoration
**Actions**:
1. Set `semptify_uid` cookie
2. Load user's vault structure from cloud
3. Verify vault integrity
4. Log reconnection event

### Step 5: Role-Based Routing
**Redirect Target**:
- Tenant → `/tenant/dashboard`  
- Advocate → `/advocate/dashboard`  
- Legal → `/legal/dashboard`  
- Manager → `/manager/dashboard`  
- Admin → `/admin/dashboard`

---

## 4. Exit Criteria

| Condition | Required |
|-----------|----------|
| `semptify_uid` cookie set | Yes |
| Storage tokens valid | Yes |
| Storage tokens verified | Yes |
| User redirected to role dashboard | Yes |
| Reconnection event logged | Yes |

---

## 5. Error Handling

| Scenario | Action | User Message |
|----------|--------|--------------|
| No journal found | Offer onboarding | "No Semptify journal found in that storage. Start fresh?" |
| Wrong provider selected | Try different provider | "Try your other storage provider?" |
| Storage access revoked | Force re-OAuth | "Please reconnect your storage" |
| Vault corrupted | Show recovery options | "Vault issue detected. Contact support?" |
| Database unavailable | Retry + error | "System unavailable. Try again?" |

---

## 6. User Experience

**Tone**: Calm, reassuring - "We're reconnecting you..."

**Screen Elements**:
- Clean centered card design
- Info box: "Semptify doesn't use email accounts"
- Provider selection (Google Drive/Dropbox/OneDrive)
- Progress indicator during reconnection
- Clear success/error messages
- "Need help?" link to support

**Timing**:
- Instant (< 1s): If tokens valid
- Brief (< 5s): If refresh needed
- OAuth flow: Provider-dependent (15-30s typical)

---

## 7. Security Considerations

- Verify OAuth tokens match expected provider
- Never expose user's refresh token in frontend
- Log all reconnection attempts (success + failure)
- Rate limit reconnection attempts per IP
- Validate session integrity before granting access

---

## 8. Implementation Files

| File | Purpose |
|------|---------|
| `static/reconnect/index.html` | UI for provider selection |
| `app/routers/storage.py` | OAuth handler + session restoration |
| `app/core/user_id.py` | User ID generation/parsing |
| `app/services/storage/` | Session management |

---

## 9. API Endpoints

### GET `/storage/auth/{provider}`
**Query**: `?return_to=/storage/reconnect`  
**Purpose**: Initiate OAuth flow

### GET `/storage/callback/{provider}`
**Query**: `?code=...&state=...`  
**Purpose**: OAuth callback, identify user by provider account, restore session

**Response**: Redirect to role-appropriate dashboard

---

**END OF CONTRACT**
