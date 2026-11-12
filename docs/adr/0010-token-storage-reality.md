# ADR 0010: OAuth Token Storage — Current Reality vs. Zero-Possession Target

Date: 2026-11-12
Status: Accepted (documents current state; vault-first migration planned)

## Context

Brad's stated architecture: user documents AND OAuth tokens live in the
user's own cloud storage; Semptify servers hold no user data beyond a
pseudonymous ID. A 2026-11-12 audit traced every token path end-to-end
(code + production Neon `sessions` table) and found the claim is not
literally true today.

## What actually exists — three stores

1. **`sessions` DB table — the live production store.**
   `save_session_to_db()` writes `access_token_encrypted` +
   `refresh_token_encrypted` at OAuth callback and on every refresh
   (`refresh_access_token` in `app/modules/storage/router.py`).
   `get_valid_session()` reads DB-only — its vault-first branch is
   commented out ("get_vault_client doesn't exist").
   Verified in prod: 1 row (google_drive) with a refresh token present.
   Encryption: `sha256(SECRET_KEY:user_id)` via `app/core/key_derivation`
   with key versioning — competent envelope encryption, but the key is
   server-derived, so DB + SECRET_KEY compromise yields every user's
   storage access.

2. **Vault via `StatelessOAuthManager` — write-only dead end.**
   `store_oauth_tokens()` runs at OAuth callback as "supplementary, for
   stateless access," but nothing in the live read path consumes it, and
   `refresh_access_token` never updates it — the vault copy goes stale
   at the first token expiry (~1h). Three provider-refresh
   implementations coexist (auto_refresh→DB, storage router→DB,
   StatelessOAuthManager→vault) and will drift.

3. **`token_manager` in-memory dict — transient cache.**
   Populated at OAuth callback and by `auto_refresh` so the immediate
   post-callback window doesn't race the DB. Holds refresh tokens in
   RAM until process restart — transient, not a store of record.

## Decision

- The `sessions` table is declared the **current** token store of
  record. Public-facing claims must say "encrypted at rest" — not
  "no user data on our servers" — until the migration below lands.
- The vault write at callback is kept deliberately: it seeds the
  migration and costs one storage call. It is documented as stale-prone,
  not relied upon.
- `token_manager` remains the request-window cache; it is not a
  persistence layer and must never become one.

## Consequences

- **Migration A (planned, needs Brad's OK — touches NO-TOUCH
  `app/modules/onboarding/`):** restore `get_vault_client`, switch
  `get_valid_session` vault-first, make refresh write vault, reduce the
  `sessions` table to metadata (no token columns). That is the real
  zero-possession end-state.
- **Until A lands:** the security perimeter that matters is
  `SECRET_KEY` + DB credentials + admin credentials — the sessions
  table is the highest-value target in the database.
- Any new code that reads/writes OAuth tokens MUST go through
  `get_valid_session`/`save_session_to_db` or `StatelessOAuthManager`
  — never a fourth path (Known Failure #16 pattern).
