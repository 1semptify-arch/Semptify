---
description: Reactive fix for vault upload reconnect loops
---

# Fix Vault Upload Reconnect Loop

## Symptom

Upload keeps redirecting to "connect your storage" and back in a loop.

## Root cause

A `/storage/status` pre-check in `static/js/core/vault-portal.js` redirects before trying the upload. When the token is expired, it creates a loop:

1. Pre-check fails → redirect to `/storage`
2. `/storage` sees a valid gate → redirect back
3. Loop repeats.

## Fix: reactive, not pre-check

1. In `static/js/core/vault-portal.js`:
   - Remove the `/storage/status` pre-check and redirect block.
   - POST directly to `/api/intake/upload/auto` (or the SSOT upload endpoint) with `user_id` from the cookie.
2. In `app/modules/intake/router.py` (or the upload endpoint), add the token fallback chain:
   ```python
   real_token = access_token
   if not real_token or real_token == "auto":
       real_token = getattr(user, "access_token", None) if user else None
   if not real_token or real_token in ("auto", "no-token"):
       try:
           from app.core.oauth_token_manager import get_valid_token_for_user
           real_token = await get_valid_token_for_user(user_id, db)
       except Exception:
           pass
   ```
3. Only if the upload fails with `401`, `token_expired`, or `storage_required`, prompt reconnect:
   ```js
   if (resp.status === 401 || ['token_expired','storage_required'].includes(result.error)) {
       if (confirm('Your storage connection expired. Reconnect now?')) {
           window.location.href = result.redirect_url
               || '/storage/reconnect?return_to=' + encodeURIComponent(window.location.pathname);
       }
   }
   ```

## Verification

- `python -m py_compile app/main.py app/modules/intake/router.py`
- Hard refresh, attempt upload, verify no loop.
