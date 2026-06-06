# Work Session Log — May 29, 2026

**Date:** May 29, 2026
**Time:** ~8:40 PM – 9:40 PM UTC-05:00
**Duration:** ~1 hour
**Commits:** `cb3a3c6`, `a503d8f`

---

## Session Overview

Two-commit session. Fixed three pre-filed issues, restructured the vault folder layout,
and relocated the reconnect flow to its architecturally correct owner.

---

## Commit 1 — `cb3a3c6` — Issue #1: route_user() async fix

### Problem
Returning tenants with documents were landing on the upload wizard instead of their dashboard.

### Root Cause
`route_user()` in `workflow_engine.py` was synchronous. When `documents_present` was not supplied
by the caller, it defaulted to `False` — sending every returning user to the upload wizard.

### Fix
- Converted `route_user()` to `async def`
- When `documents_present is None`, now awaits `VaultUploadService.get_user_documents()` directly
- Falls back to `False` on query failure (safe default, logged as warning)
- Updated all call sites with `await` across 7 files:
  - `app/core/workflow_engine.py`
  - `app/modules/preamble/router.py`
  - `app/modules/onboarding/router.py`
  - `app/modules/storage/router.py`
  - `app/modules/role_ui/router.py`
  - `app/modules/workflow_validator/router.py`
  - `app/main.py` — `_guard_role_page()` made async, all 18 call sites awaited

---

## Commit 2 — `a503d8f` — Issues #2 & #3 + Vault Restructure + Reconnect Relocation

### Issue #2: Gate Config Mismatch (app/modules/onboarding/config.py)
- **Problem:** Config declared 2 gates; runtime checked and marked 3 (including `document_uploaded`)
- **Fix:** Added `document_uploaded` to `config.gates` default list
- **Result:** Status page `get_first_incomplete_gate()` now correctly detects incomplete pipeline

### Issue #3: Silent DB Error in Preamble (app/modules/preamble/router.py)
- **Problem:** DB failure silently redirected user to role selection — potential loop, lost context
- **Fix:** DB errors now return an honest **503 HTML page** with:
  - "Having trouble connecting — your data is safe"
  - **Try Again** button (reloads `/preamble`)
  - **Start Fresh** button (clears cookie → role selection, intentional)
- Upgraded `logger.warning` → `logger.error` so monitoring catches it

### Vault Path Restructure (app/core/vault_paths.py)
**Before:**
```
Semptify5.0/
├── Vault/          ← user files
├── auth/           ← system tokens (visible!)
└── vault/          ← system metadata (confusing duplicate of Vault/)
```
**After:**
```
Semptify5.0/
├── Vault/          ← user files (documents, certs, timeline, overlays)
└── .semptify/      ← hidden system config (dot-prefix hidden from casual browsing)
    ├── auth/       ← token.enc, device_keys.json, provisioning.json
    └── vault/      ← manifest.json, README.md
```
- Added `SYSTEM_FOLDER` constant as required parent folder
- `config.py` updated to include `SYSTEM_FOLDER` in `CANONICAL_VAULT_FOLDERS` before its children

### Reconnect Relocation (app/modules/onboarding/reconnect.py — NEW FILE)
- **Problem:** `/storage/reconnect` lived in `storage/router.py` — wrong owner
- **Why it matters:** Reconnect restores the `storage_connected` gate. That gate is owned by
  the onboarding module. Storage should be infrastructure only (token refresh, health checks, APIs)
- **Fix:**
  - Created `app/modules/onboarding/reconnect.py` with full reconnect logic
  - Mounts at `/storage/reconnect` (same URL — zero impact on other code)
  - Registered in `app/core/product_manifest.py` CORE tier
  - Removed handler + HTML generator from `storage/router.py`
  - Removed static-file stub from `app/main.py`
  - **Also fixed:** `_get_all_provider_buttons` was called in old code but never defined — silent runtime bug

---

## Architecture Decisions Made This Session

1. **Vault hidden system folder:** `.semptify/` chosen over `system/` — dot-prefix is the convention
   for programmatically-managed folders that users shouldn't touch (proven on Dropbox + Drive)

2. **Reconnect URL stays at `/storage/reconnect`:** Moving the handler doesn't require changing
   the URL. 175 references to that path stay untouched. Clean ownership, zero blast radius.

3. **3-gate model confirmed:** `storage_connected` → `vault_initialized` → `document_uploaded`
   Each gate tests a distinct system layer. Conflating them makes debugging harder.

---

## Files Changed

| File | Change |
|------|--------|
| `app/core/workflow_engine.py` | `route_user()` → async, vault query on None |
| `app/core/vault_paths.py` | New `.semptify/` structure + `SYSTEM_FOLDER` |
| `app/core/product_manifest.py` | Register `onboarding.reconnect` in CORE tier |
| `app/modules/onboarding/config.py` | Add `SYSTEM_FOLDER` + `document_uploaded` gate |
| `app/modules/onboarding/reconnect.py` | **NEW** — owns `/storage/reconnect` |
| `app/modules/preamble/router.py` | Honest 503 DB error page + `await route_user` |
| `app/modules/onboarding/router.py` | `await route_user` at 2 call sites |
| `app/modules/storage/router.py` | Remove reconnect handler/HTML; `await _route_user` at 4 sites |
| `app/modules/role_ui/router.py` | `await _route_user` |
| `app/modules/workflow_validator/router.py` | `await route_user` at 2 sites |
| `app/main.py` | `_guard_role_page` async; remove reconnect stub; 18 call sites awaited |

---

## Pending Next Session

- **Live test:** Full onboarding with new `.semptify/` vault path layout
- **Live test:** Returning user → confirm landing on tenant home (not upload wizard)
- ContextDataLoop cross-source enrichment
- Fix `/api/analytics/pageview` 404
- Build generic module page template (`/tool/{module_name}`)
