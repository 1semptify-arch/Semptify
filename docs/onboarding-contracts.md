# Onboarding End-to-End Contracts

## Overview

This document defines the complete onboarding flow with explicit steps, contracts, and completion criteria for Semptify 5.0.

## Current State Analysis

### Existing Gates (2-gate system)

```python
gates = ["storage_connected", "vault_initialized"]
```text

**Issues identified:**

- `vault_initialized` is marked during OAuth callback (blocking)
- No verification that vault folders actually work
- Onboarding considered "complete" before user reaches their homepage
- No explicit handoff to product workflow

## Proposed Onboarding Flow

### Step 1: Role Selection (Process A)

**Entry Point:** `/` or `/onboarding/start`
**Contract:**

- Input: User selects role from available options
- Output: Role stored in OAuth state, redirect to provider selection
- Success Criteria: Role parameter valid and persisted

### Step 2: Storage Provider Connection

**Entry Point:** `/onboarding/providers`
**Contract:**

- Input: User selects provider (Google Drive, Dropbox, OneDrive)
- Output: OAuth redirect to provider
- Success Criteria: OAuth initiation successful, state token created

### Step 3: OAuth Callback (Non-blocking)

**Entry Point:** `/onboarding/callback/{provider}`
**Contract:**

- Input: Authorization code + state from provider
- Output: User created, session saved, storage_connected gate marked
- **CRITICAL:** Do NOT block on vault creation
- Success Criteria:
  - User record exists in database
  - OAuth tokens cached
  - storage_connected gate marked
  - Redirect to vault-setup page (not homepage)

### Step 4: Vault Setup with Loading Screen

**Entry Point:** `/onboarding/vault-setup`
**Contract:**

- Input: Authenticated user with storage_connected gate
- Process:
  1. Show "Please be patient — 10–30 seconds" message
  2. Display rotating "Did you know?" facts
  3. Create vault folders via API call
  4. Verify folder accessibility
- Output: vault_initialized gate marked + redirect to complete
- Success Criteria:
  - All canonical vault folders created
  - Folder accessibility verified (read/write test)
  - vault_initialized gate marked

### Step 5: Onboarding Complete (Handoff)

**Entry Point:** `/onboarding/complete`
**Contract:**

- Input: User with both gates marked
- Output: Route user to their role-specific homepage
- Success Criteria: User lands on productive homepage with full access

## Completion Definition

**Onboarding is COMPLETE when:**

1. `storage_connected` gate is marked (OAuth successful)
2. `vault_initialized` gate is marked (folders created AND verified)
3. User successfully lands on their role-specific homepage
4. Homepage loads without errors and shows productive UI

**NOT complete when:**

- Only OAuth callback finished (vault not verified)
- Vault folders created but not tested
- User still on onboarding pages
- Homepage shows errors or missing permissions

## Step Contracts Detail

### Step 1: Role Selection Contract

```python
## Input validation
ALLOWED_ROLES = {"tenant", "advocate", "legal", "admin", "manager"}

## Success output
{
    "role": "tenant",
    "next_step": "provider_selection",
    "redirect": "/onboarding/providers?role=tenant"
}
```

### Step 2: Provider Selection Contract

```python
## Provider validation
ALLOWED_PROVIDERS = {"google_drive", "dropbox", "onedrive"}

## OAuth state creation
{
    "state": "kZDck5dVuGWpJqVpwoKToF0H4Rcy2SbltqYPTtnWSKA",
    "provider": "google_drive",
    "role": "tenant",
    "callback_url": "https://semptify.org/onboarding/callback/google_drive"
}
```text

### Step 3: OAuth Callback Contract

```python
## Token exchange success
{
    "user_id": "goog_tenant_abc123",
    "is_new": true,
    "storage_connected": true,
    "vault_initialized": false,  # Always false - force vault-setup
    "redirect": "/onboarding/vault-setup"
}

## Error handling
{
    "error": "invalid_code",
    "redirect": "/onboarding/providers?error=oauth_failed"
}
```

### Step 4: Vault Setup Contract

```python
## API: POST /onboarding/api/vault/init
{
    "success": true,
    "folders_created": [
        "Semptify5.0",
        "Semptify5.0/Vault",
        "Semptify5.0/Vault/documents",
        # ... all canonical folders
    ],
    "failed_folders": []
}

## API: GET /onboarding/api/vault/verify
{
    "accessible": true,
    "ok": true,
    "test_results": {
        "write_test": "passed",
        "read_test": "passed",
        "list_test": "passed"
    },
    "error": null
}
```text

### Step 5: Complete Handoff Contract

```python
## Route decision based on role
{
    "tenant": "/tenant/home",
    "advocate": "/advocate/home", 
    "legal": "/legal/home",
    "admin": "/admin/home",
    "manager": "/manager/home"
}

## Homepage validation
{
    "loads_without_error": true,
    "user_context_valid": true,
    "storage_accessible": true,
    "productive_ui_visible": true
}
```

## Error Recovery Paths

### OAuth Failure

- Redirect back to provider selection with error message
- Preserve selected role in session

### Vault Creation Failure

- Show specific error message on vault-setup page
- Provide "Retry" button
- Offer "Contact Support" option after 3 failures

### Verification Failure

- Show "Vault created but verification failed"
- Attempt repair automatically
- Fall back to manual repair flow

## Implementation Checklist

### Required Changes

- [ ] Update OAuth callback to never block on vault creation
- [ ] Add vault verification API endpoint
- [ ] Implement rotating facts display on vault-setup page
- [ ] Update onboarding completion criteria
- [ ] Add homepage validation in complete step
- [ ] Update error handling and recovery paths

### Tests Required

- [ ] End-to-end onboarding flow test
- [ ] OAuth callback non-blocking test
- [ ] Vault creation failure test
- [ ] Verification failure test
- [ ] Homepage handoff test

## Metrics to Track

- Step completion rates
- Time spent per step
- Drop-off points
- Error rates by step
- Time to productive homepage

## Security Considerations

- OAuth state tokens must expire in 15 minutes
- Vault verification must use user's actual permissions
- No sensitive data in loading screen facts
- Rate limiting on OAuth initiation
- Secure cookie handling for user context
