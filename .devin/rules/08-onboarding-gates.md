---
description: Onboarding gate system and module status
---

# Onboarding Gates

Canonical implementation lives in `app/modules/onboarding/`.

## Gates (two only)

1. `storage_connected` — OAuth completed to the user's cloud drive.
2. `vault_initialized` — Vault folders created; user is active.

`client_activated` was removed on 2026-05-12. Do not reintroduce it.

## Activation requirements

- Add `register_onboarding(app, config)` to `main.py`.
- Disable the old `onboarding_router` in `main.py`.
- Remove the onboarding OAuth callback from `storage.py`.
- Test on Render.

## Design notes

- Onboarding is gate-driven, not flag-driven. Route based on `vault_initialized`.
- Own OAuth callback at `/onboarding/callback/{provider}` (separate from storage reconnect).
- Config defaults vault folders from `app/core/vault_paths.py`.
- Token cached immediately via `token_manager.store_token()`.
- All redirects must be SSOT-compliant.
