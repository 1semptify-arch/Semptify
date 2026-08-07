# ADR 0001: Storage Architecture Split

Date: 2026-08-06
Status: Accepted

## Decision

Vault storage is split across pluggable providers (Dropbox, Google Drive, OneDrive) behind a unified provider interface in `app/services/storage`, with path resolution centralized in `app/core/vault_paths.py` and cross-cutting concerns (token refresh, provider selection) handled by `app/core/storage_middleware.py` and `app/core/oauth_token_manager.py`. The canonical vault root folder `.Semptify5.0` is the first entry in `CANONICAL_VAULT_FOLDERS` and must be created explicitly before any nested folder.

## Why

Tenants arrive with different existing cloud storage. Forcing a single provider would block adoption. A provider-agnostic interface lets onboarding route to whichever provider the tenant authorized, while keeping the vault folder structure identical across providers.

The `.Semptify5.0` parent-first rule is a hard constraint of the Dropbox API (and good practice generally): nested folder creation fails if the parent does not exist. This was learned the hard way — see Known Failure #3 in `AGENTS.md`.

## Consequences

- Any new storage provider MUST implement the provider interface in `app/services/storage` and register through `app/core/oauth_token_manager.get_valid_token_for_user()` + `app/services/storage.get_provider()` + `app/core/user_id.get_provider_from_user_id()`. Do not invent a parallel factory (see Known Failure #16 — the hallucinated `app.core.storage_factory`).
- Token refresh and provider I/O called from async routes MUST use async paths (`app/core/auto_refresh.ensure_valid_token()`), never the synchronous `token_manager.refresh_token_if_needed()` (Known Failure #19).
- Vault folder creation MUST check `create_folder()` return values and raise `RuntimeError` on failure (Known Failure #1). Empty folders are valid — only an exception from `list_files()` indicates a missing folder (Known Failure #4).
- Single API calls behind Cloudflare MUST stay under ~20s of work — split folder creation from file creation across steps (Known Failure #5).
