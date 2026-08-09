# Semptify — SWE 1.6 Handoff Instructions

## Updated: 2026-06-18 PM | For: Next AI session (SWE 1.6)

---

## WHO YOU ARE AND WHAT THIS IS

You are an AI coding assistant working on **Semptify** — a tenant rights advocacy platform
built in Python 3.11.9 / FastAPI / PostgreSQL / Redis / SQLAlchemy (async).

This is a production system serving real tenants who may be facing eviction, housing
discrimination, or landlord retaliation. These are stressed people with limited time and
money. Your work directly affects their ability to organize their evidence and protect
their legal rights.

**Your responsibility:** Write correct, careful, tested code. Never take shortcuts that
could silently break data integrity. Never ship without a compile check.

---

## MANDATORY PRE-FLIGHT — DO THIS BEFORE ANY CODE CHANGE

```powershell
## 1. Activate the correct Python environment (3.11.9 — non-negotiable)
.\venv311\Scripts\Activate.ps1

## 2. Read the current state
## - READ BUILD_STATE.md (top section = last session)
## - READ ACTIVE_CONTEXT.md (what is in progress RIGHT NOW)
## - READ AGENTS.md Known Failure Registry (do not repeat these bugs)

## 3. Compile check core files BEFORE touching anything
python -m py_compile app/main.py app/core/navigation.py app/modules/vault/router.py app/modules/onboarding/router.py app/modules/documents/router.py app/services/vault_upload_service.py
```python

If any file fails to compile at pre-flight, **stop and report it to the user** before
doing anything else. Do not proceed on a broken baseline.

---

## WHERE THINGS ARE

```

c:\Semptify\Semptify-FastAPI\        ← repo root (cwd for all commands)
  app/
    main.py                          ← FastAPI app + lifespan + all router registration
    core/
      navigation.py                  ← SSOT for all URL paths (use get_stage(), never hardcode)
      capabilities.py                ← User feature access control (Redis cache + DB)
      event_bus.py                   ← Pub/sub for cross-module events
      event_subscribers.py           ← All event subscriptions (registered at startup)
      utc.py                         ← utc_now() — ALWAYS use this, never datetime.now()
      database.py                    ← get_db_session() async context manager
      id_gen.py                      ← make_id("prefix") for all new IDs
      onboarding_state.py            ← 2-gate SSOT: storage_connected + vault_initialized
      module_contracts.py            ← FunctionGroupContract registry (SSOT for APIs)
    models/
      models.py                      ← ALL SQLAlchemy models (38 tables)
      unified_overlay_models.py      ← CreateOverlayRequest, UnifiedOverlay, etc.
    modules/
      vault/router.py                ← SSOT upload entry point (all uploads go here)
      onboarding/router.py           ← Onboarding flow (3 internal gates)
      storage/router.py              ← OAuth callbacks, provider connect/reconnect
      capabilities/router.py         ← Admin CRUD for user capabilities
      timeline/router.py             ← /api/timeline/unified
      case_builder/router.py         ← DB-backed case management (incidents table)
      unified_overlays/router.py     ← SSOT overlay API (create/list/get/update/delete/compose)
      filedored/router.py            ← Browse + list folders
      rent/router.py                 ← Rent payment CRUD
      user/router.py                 ← Role impersonation act-as endpoints
      court_forms/router.py          ← Court form generation + autofill
      admin_console/router.py        ← Admin dashboard API
    services/
      vault_upload_service.py        ← VaultUploadService — the one upload pipeline
      unified_overlay_manager.py     ← SSOT overlay CRUD + 5 overlay contracts
      timeline_extraction.py         ← NLP date/event extraction from documents
      communication_service.py       ← Conversations + messages (overlay-backed)
      document_delivery_service.py   ← Send/sign/reject documents (overlay-backed)
      filedored_service.py           ← Document sorting + folder creation
      duplicate_detection_service.py ← Duplicate detection across uploads
      timeline_chronology.py         ← Timeline ordering logic
  alembic/
    versions/                        ← ALL database migrations (must chain correctly)
  tests/
    e2e/                             ← Playwright smoke tests (run against semptify.org)
  BUILD_STATE.md                     ← Session log + what is known working/broken
  ACTIVE_CONTEXT.md                  ← What is in progress RIGHT NOW
  AGENTS.md                          ← Rules + Known Failure Registry (READ THIS)

```text

---

## WHAT WAS DONE THIS SESSION (2026-06-18 PM)

**HEAD: `8fd6333` — clean, pushed to origin/main**

### Overlay System Mechanics Alignment

- Fixed `CreateOverlayRequest` signature in 3 files:
  - `app/services/filedored_service.py`
  - `app/services/duplicate_detection_service.py`
  - `app/modules/filedored/router.py`
  - Replaced `vault_id/user_id/overlay_path/overlay_data` with `document_id/vault_path/payload/metadata`
- Replaced phantom `app.core.storage_factory` import in 3 files with real pattern:
  - `oauth_token_manager.get_valid_token_for_user()` + `services.storage.get_provider()` + `user_id.get_provider_from_user_id()`
- Replaced non-existent `get_overlays_by_type` / `get_overlays_by_path` with `get_overlays()` + in-memory filtering
- Retired 943-line dead `app/modules/overlays/router.py` (deleted entire directory)
- `app/modules/unified_overlays/router.py` is now the sole SSOT overlay API

### FunctionGroupContract Registry — 34 contracts across 11 services

- **vault** (3): `vault_upload`, `vault_folders`, `vault_init`
- **overlays** (5): `overlay_create`, `overlay_query`, `overlay_update`, `overlay_delete`, `overlay_compose_view`
- **communication** (4): `conversation_create`, `message_send`, `conversations_list`, `document_fill_sign`
- **delivery** (4): `document_send`, `inbox_list`, `document_sign`, `document_reject`
- **filedored** (2): `document_process`, `folders_ensure`
- **duplicates** (2): `detect`, `list_all`
- **court_forms** (2): `form_generate`, `form_autofill`
- **timeline** (1): `timeline_chronology`
- **rent** (5): `payment_create`, `payment_list`, `payment_get`, `payment_update`, `payment_delete`
- **user** (2): `act_as_start`, `act_as_stop`
- **admin_console** (5): `user_list`, `user_detail`, `impersonate_start`, `impersonate_stop`, `system_status`

All contracts registered at import time and visible in the admin contract browser.

### AGENTS.md Updated

- Added **Failure #16: Hallucinated Overlay API Signatures** to Known Failure Registry
- Added **Module Contract Mandate** section
- Rule: "Before writing code that calls another service's API, check the contract registry first."

### /review Bugs Fixed

- `filedored/router.py:198`: `overlay.overlay_path` → `overlay.vault_path` (AttributeError)
- `filedored_service.py`: added `original_filename` to payload (router was showing "Unknown")
- `duplicate_detection_service.py:79-88`: replaced stale `create_overlay` with `update_overlay()` per contract

### Previous Session (2026-06-18 AM)

- Fixed registration bug (unhashable type 'dict')
- Deleted PII-collecting register forms, redirected to OAuth onboarding
- Updated Playwright tests to use OAuth flow
- Deployed to Render

### Earlier Sessions (2026-06-16)

- Milestones 1–9 completed: case builder DB, timeline end-to-end, capability system, datetime.now() purge, event bus fixes, missing migrations

---

## CURRENT STATE — WHAT IS KNOWN WORKING

- ✅ All core files compile clean (verified at end of session)
- ✅ Git working tree clean, HEAD = `8fd6333` pushed to origin/main
- ✅ `grep datetime.now()` across `app/` → 0 results (regression-free)
- ✅ Overlay system contracts are SSOT for all overlay APIs
- ✅ Cloudflare dev mode ON (purged at end of session — 3hr window)
- ✅ Render auto-deploying main

---

## WHAT IS PENDING (NEXT PRIORITIES)

Pick up in this order:

### Priority 1 — GUI Development for Overlay System

The overlay **mechanics** are now solid. Next is the user-facing surface.

1. **Minimal document viewer** — load a vault document and list its overlays
2. **Annotation toolbar** — add highlight + note overlays
3. **Redaction / watermark compose view** — use `overlay_compose_view` contract

Files to touch:

- `static/` (new or existing page)
- `app/modules/unified_overlays/router.py` (already has endpoints)
- `app/services/unified_overlay_manager.py` (contracts at bottom are SSOT)

### Priority 2 — Live Verification (Manual)

These require real OAuth login in a browser:

1. **Filedored browse folder**: `GET /api/filedored/browse/{folder}` should list documents
2. **Duplicate detection**: upload same file twice, check second returns `is_duplicate: true`
3. **Court forms**: generate form creates a `FORM_FILL` overlay
4. **Contract browser**: admin dashboard shows 34 contracts

### Priority 3 — Remaining Contracts (When Those Services Are Touched)

- `case_builder`
- `fems`
- `timeline_events`
- `onboarding`
- `documents`
- `preamble`
- `cloud_sync`

---

## ARCHITECTURE RULES — NEVER VIOLATE THESE

### 1. datetime — Always UTC

```python
## WRONG — creates naive datetime (no timezone)
from datetime import datetime
ts = datetime.now()

## RIGHT — always timezone-aware UTC
from app.core.utc import utc_now
ts = utc_now()
```

### 2. SSOT Redirects — Never Hardcode URLs

```python
## WRONG
return RedirectResponse(url="/onboarding/providers")

## RIGHT
providers_stage = navigation.get_stage("providers")
return ssot_redirect(providers_stage.path, context="my_function reason")
```text

### 3. Database Sessions — Use the Context Manager

```python
## WRONG
session = AsyncSessionLocal()  # does not exist

## RIGHT
from app.core.database import get_db_session
async with get_db_session() as session:
    result = await session.execute(...)
```

### 4. IDs — Use make_id()

```python
## WRONG
import uuid; id = str(uuid.uuid4())

## RIGHT
from app.core.id_gen import make_id
id = make_id("tevt")  # → "tevt_a1b2c3d4..."
```text

### 5. Exception Handling — Never Bare except

```python
## WRONG
try:
    ...
except:
    pass

## RIGHT — specific, always log
try:
    ...
except ValueError as e:
    logger.error("context: %s", e)
    raise
```

### 6. Imports — Always at Top of File

Never inject imports mid-function if avoidable. If a lazy import is necessary (circular
dependency), document why.

### 7. New Tables — Always Create Alembic Migration

Never rely on `Base.metadata.create_all()` in production. Every new model needs a migration.
Chain it correctly: set `down_revision` to the current head before writing.

Get current head first:

```powershell
python -m alembic heads
```text

### 8. File Rewrites — Never Create _v2 Files

If a file needs a rewrite, ask the user to rename the original to `_old.py` first.
Then write the new version into the original filename. Never create `_v2`, `_new`, `_fixed`.

### 9. Module Contracts — SSOT for API Signatures

Every reusable service API must register a `FunctionGroupContract` in `app/core/module_contracts.py`.
Before writing code that calls another service, read the contract.

Pattern:

```python
from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(FunctionGroupContract(
    module="<module>",
    group_name="<group>",
    title="<Title> (SSOT)",
    description="CANONICAL ... What it does. What it does NOT do.",
    inputs=("<required>", "<optional>?"),
    outputs=("<output>",),
    dependencies=("app.services.<module>",),
    deterministic=True,
))
```

---

## KNOWN FAILURE REGISTRY SUMMARY (from AGENTS.md)

These have each cost multiple sessions to debug. Read the full registry in AGENTS.md.
Short summary:

1. **Vault folder creation** — check return value of every create_folder() call. Raise on failure.
2. **Dropbox 409 errors** — only `folder_name_exists` is success. All other 409s must raise.
3. **Missing parent vault folder** — `.Semptify5.0` must be FIRST in CANONICAL_VAULT_FOLDERS.
4. **Empty folder ≠ missing** — `verify_vault_folders()` must only fail if exception, not empty list.
5. **Cloudflare 504** — single endpoint must not do >20s of work. Split into steps.
6. **Import injection** — NEVER inject imports mid-file. Always at top.
7. **Bare except** — NEVER use bare `except:`. Always specific type.
8. **datetime.now()** — NEVER use without timezone. Always `utc_now()`.
9. **SSOT navigation** — NEVER hardcode URL strings in redirects. Always `navigation.get_stage()`.
10. **VaultResult missing from exports** — any new class used outside its module needs `__init__.py` export.
11. **Duplicate exception handlers** — check for duplicates before adding new ones in `main.py`.
12. **Cloudflare tunnel** — run as a service (`sc config cloudflared start= auto`), not manually.
13. **File rewrite cascading** — never create `_v2` files. Ask user to rename original first.
14. **Wrong Python version** — always use `venv311`. Python 3.11.9 only. Never 3.12+.
15. **Workaround instead of root cause** — fix the source, not the symptom. Band-aids compound.
16. **Hallucinated overlay API signatures** — read the contracts in `unified_overlay_manager.py` before touching overlays. No `vault_id/user_id/overlay_path/overlay_data` on `CreateOverlayRequest`. No `get_overlays_by_type/path` methods.

---

## HOW TO SHIP AT END OF SESSION

Run `/ship` workflow or manually:

```powershell
## 1. Compile check
python -m py_compile app/main.py app/core/navigation.py app/modules/vault/router.py \
  app/modules/onboarding/router.py app/modules/documents/router.py \
  app/services/vault_upload_service.py

## 2. Stage + commit
git add app/ static/ tests/ scripts/ alembic/ render.yaml Dockerfile requirements.txt \
  pyproject.toml AGENTS.md BUILD_STATE.md ACTIVE_CONTEXT.md
git commit -m "one-line summary

- file: what changed and why
- file: what changed and why"

## 3. Push
git push origin main

## 4. Verify
git log --oneline -3

## 5. Update BUILD_STATE.md with what was done, then:
git add BUILD_STATE.md && git commit -m "docs: update BUILD_STATE" && git push origin main
```text

Render auto-deploys from main. Check <https://dashboard.render.com> for deploy logs.
The deploy runs `alembic upgrade head` automatically before starting the server.

---

## USEFUL DIAGNOSTIC COMMANDS

```powershell
## Check for naive datetime calls (should always be 0)
grep -r "datetime\.now()" app/ --include="*.py"

## Check Alembic migration state
python -m alembic heads
python -m alembic current

## Check all model tables vs migrations coverage
python -c "from app.models.models import Base; print('\n'.join(sorted(Base.metadata.tables.keys())))"

## Compile check a specific file
python -m py_compile app/modules/vault/router.py && echo OK

## Check for bare excepts
grep -rn "except:" app/ --include="*.py"

## Check for mutable defaults
grep -rn "def .*=\[\]" app/ --include="*.py"
grep -rn "def .*={}" app/ --include="*.py"

## Check contract registry count (from a running Python shell)
python -c "from app.core.module_contracts import registry; print(len(registry.groups))"
```

---

## PRODUCTION URLS

- App: <https://semptify.org>
- Render dashboard: <https://dashboard.render.com>
- API health: <https://semptify.org/health>

---

*This file was written at end of session 2026-06-18 PM for handoff to the next AI agent.*
*Ground truth is always BUILD_STATE.md + ACTIVE_CONTEXT.md. Read those first.*
