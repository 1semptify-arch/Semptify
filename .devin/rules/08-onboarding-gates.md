---
description: Onboarding gate system and module status
---

# Onboarding Gates

Canonical implementation lives in `app/modules/onboarding/`.

## Gates (three — declared in `app/modules/onboarding/config.py`)

1. `storage_connected` — OAuth completed to the user's cloud drive.
2. `vault_initialized` — vault fully proven: folders, files, token backup, and a live write/read probe all pass. Marked only at the end of vault setup — never on folder creation alone.
3. `document_uploaded` — marked once the first real document is deposited into the vault (written to the tenant's own cloud drive, read back, certified, registered, timeline entry, event emitted). The vault is the document's permanent home — this gate proves it can receive and hold one.

`client_activated` was removed on 2026-05-12. Do not reintroduce it.

## Where enforcement actually lives

`app/core/onboarding_state.py` is the live enforcement path (consumed by `StorageRequirementMiddleware`). It reads all three gates. A user with `storage_connected` and `vault_initialized` but not `document_uploaded` is routed to `/onboarding/vault-setup/inspect`.

`OnboardingGateMiddleware` in `app/modules/onboarding/middleware.py` is **not registered** — `app/main.py` passes `enable_gate_middleware=False`, so `register_onboarding()` skips `add_middleware`. Its `gate_routes` dict is dead code in production and editing it changes nothing at runtime. Two prior agent sessions lost time there. Gate-enforcement changes go in `app/core/onboarding_state.py`.

## Corrections (2026-09-15)

- This file previously said the `vault_initialized` and `document_uploaded` marks are "written atomically." **False in code:** `mark_gate()` commits inside itself (`gates.py`). The two marks are now at separate endpoints — `vault_initialized` at the end of `POST /api/vault/security` and `document_uploaded` at the end of `POST /api/vault/verify` — so a crash after step 2 leaves `vault_initialized` set and `document_uploaded` unset, routing the user to `/onboarding/vault-setup/inspect`.
- The 2026-09-12 decision that `document_uploaded` is a passive proof receipt was **superseded 2026-09-15**: Brad decided it is an enforced third gate that completes onboarding, and that vault creation gets split from vault completion so the vault no longer waits on a user document. This work has landed in `app/core/onboarding_state.py` and `app/modules/onboarding/router.py`.

## Activation requirements

- Add `register_onboarding(app, config)` to `main.py`.
- Disable the old `onboarding_router` in `main.py`.
- Remove the onboarding OAuth callback from `storage.py`.
- Test on Render.

## Design notes

- Onboarding is gate-driven, not flag-driven. Route based on the first incomplete gate in `storage_connected` → `vault_initialized` → `document_uploaded`.
- Own OAuth callback at `/onboarding/callback/{provider}` (separate from storage reconnect).
- Config defaults vault folders from `app/core/vault_paths.py`.
- Token cached immediately via `token_manager.store_token()`.
- All redirects must be SSOT-compliant.
