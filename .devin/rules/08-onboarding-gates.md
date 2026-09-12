---
description: Onboarding gate system and module status
---

# Onboarding Gates

Canonical implementation lives in `app/modules/onboarding/`.

## Gates (three — declared in `app/modules/onboarding/config.py`)

1. `storage_connected` — OAuth completed to the user's cloud drive.
2. `vault_initialized` — vault fully proven: folders, files, token backup, and a live write/read probe all pass. Marked only at the end of vault setup — never on folder creation alone.
3. `document_uploaded` — proof-receipt gate, marked atomically with `vault_initialized` after the first real document completes the full pipeline (certificate, registry, overlay, timeline, event bus). A vault is not considered active until a document has actually flowed through it.

`client_activated` was removed on 2026-05-12. Do not reintroduce it.

Live enforcement reads `storage_connected` + `vault_initialized` via `app/core/onboarding_state.py`. Whether `document_uploaded` should become an enforced gate versus staying a proof receipt is an open Brad decision (`orchestrator_state.json` → `onboarding-third-gate-adr0002-2026-09-11`).

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
