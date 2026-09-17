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

`app/core/onboarding_state.py` is the live enforcement path (consumed by `StorageRequirementMiddleware`). It reads `storage_connected` + `vault_initialized` only.

`OnboardingGateMiddleware` in `app/modules/onboarding/middleware.py` is **not registered** — `app/main.py` passes `enable_gate_middleware=False`, so `register_onboarding()` skips `add_middleware`. Its `gate_routes` dict is dead code in production and editing it changes nothing at runtime. Two prior agent sessions lost time there. Gate-enforcement changes go in `app/core/onboarding_state.py`.

## Corrections (2026-09-15)

- This file previously said the `vault_initialized` and `document_uploaded` marks are "written atomically." **False in code:** `mark_gate()` commits inside itself (`gates.py`), so the two calls at the end of `POST /api/vault/verify` are two sequential commits. A crash between them leaves vault-marked/document-unmarked. The consequence is bounded — `/onboarding/complete` and the `/onboarding/status` page both route such a user to `/onboarding/vault-setup/inspect` — but do not rely on the atomicity claim.
- The 2026-09-12 decision that `document_uploaded` is a passive proof receipt was **superseded 2026-09-15**: Brad decided it is an enforced gate that completes onboarding, and that vault creation gets split from vault completion so the vault no longer waits on a user document. See `handoffs/onboarding-full-rebuild-spec-2026-09-16.md` — the canonical onboarding spec (supersedes `onboarding-rewrite-2026-09-15.md`, including removal of the upload-first/pending-doc mechanics). Until that lands, live behaviour is as described above.

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
