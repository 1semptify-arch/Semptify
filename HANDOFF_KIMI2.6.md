# Semptify — Kimi 2.6 Handoff Instructions
# Prepared: 2026-06-16 | For: Next AI session (Kimi 2.6)

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
# 1. Activate the correct Python environment (3.11.9 — non-negotiable)
.\venv311\Scripts\Activate.ps1

# 2. Read the current state
# - READ BUILD_STATE.md (top section = last session)
# - READ ACTIVE_CONTEXT.md (what is in progress RIGHT NOW)
# - READ AGENTS.md Known Failure Registry (do not repeat these bugs)

# 3. Compile check core files BEFORE touching anything
python -m py_compile app/main.py app/core/navigation.py app/modules/vault/router.py app/modules/onboarding/router.py app/modules/documents/router.py app/services/vault_upload_service.py
```

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
    models/
      models.py                      ← ALL SQLAlchemy models (38 tables)
    modules/
      vault/router.py                ← SSOT upload entry point (all uploads go here)
      onboarding/router.py           ← Onboarding flow (3 internal gates)
      storage/router.py              ← OAuth callbacks, provider connect/reconnect
      capabilities/router.py         ← Admin CRUD for user capabilities
      timeline/router.py             ← /api/timeline/unified
      case_builder/router.py         ← DB-backed case management (incidents table)
    services/
      vault_upload_service.py        ← VaultUploadService — the one upload pipeline
      timeline_extraction.py         ← NLP date/event extraction from documents
  alembic/
    versions/                        ← ALL database migrations (must chain correctly)
  tests/
    e2e/                             ← Playwright smoke tests (run against semptify.org)
  BUILD_STATE.md                     ← Session log + what is known working/broken
  ACTIVE_CONTEXT.md                  ← What is in progress RIGHT NOW
  AGENTS.md                          ← Rules + Known Failure Registry (READ THIS)
  AGENTS.md Known Failure Registry   ← 15 documented recurring bugs — DO NOT REPEAT THEM
```

---

## WHAT WAS DONE THIS SESSION (2026-06-16)

All 6 milestones shipped and pushed to `origin/main`. Current HEAD: `6bb0fa3`

### Milestone 1 — Case Builder + Vault Foundation
- Case builder storage moved from local JSON files → PostgreSQL `incidents.incident_metadata`
- Cases now survive Render restarts
- Filedored idempotency: Redis flag skips 17 API calls on repeat uploads
- Playwright smoke tests wired up (8 tests, `tests/e2e/onboarding_smoke.spec.js`)

### Milestone 2 — Timeline End-to-End
- `_cloud_event_to_item()` Pydantic field names fixed (would have crashed timeline for all users)
- Upload → timeline wired: `event_subscribers.py` `_on_document_added()` writes `TimelineEvent` row on upload
- Timeline smoke tests (4 tests, `tests/e2e/timeline_smoke.spec.js`)

### Milestone 3 — Capability System Audit
- Full audit confirmed Capability System already built and wired
- `user_capabilities` table, Redis cache, `seed_capability_defaults` on every login
- Capability smoke tests (7 tests, `tests/e2e/capabilities_smoke.spec.js`)

### Milestone 4 — datetime.now() Purge
- 13 occurrences of naive `datetime.now()` found across 8 files — ALL replaced with `utc_now()`
- Files: `inventory/router.py`, `vault_installer/routes.py`, `document_converter/converter.py`,
  `ai_tool_crib.py`, `contracts_framework.py`, `accountability_planner.py`,
  `inventory_manager.py`, `timeline_extraction.py`
- `grep datetime.now()` across `app/` → **0 results**

### Milestone 5 — Event Bus Fixes
- `Event.timestamp` in `event_bus.py` used `datetime.now` as default factory — fixed to `utc_now`
- `notify_document_added()` existed but was NEVER called — wired it in `vault/router.py`
  after the audit log, fire-and-forget `asyncio.create_task`
- Full upload → timeline chain now live end-to-end

### Milestone 6 — Missing Alembic Migrations
- Scanned all 38 tables in `Base.metadata` vs all migration files
- Found 2 tables with ZERO migration coverage:
  - `admin_audit_logs` (AdminAuditLog) — admin action audit trail
  - `document_annotations` (DocumentAnnotation) — footnote/highlight indexing
- Created migration: `alembic/versions/20260616_add_admin_audit_logs_and_document_annotations.py`
- New Alembic head: `20260616_add_missing_tables`

---

## CURRENT STATE — WHAT IS KNOWN WORKING

- ✅ All core files compile clean (verified at end of session)
- ✅ Git working tree clean, HEAD = `6bb0fa3` pushed to origin/main
- ✅ Alembic single clean head: `20260616_add_missing_tables`
- ✅ `grep datetime.now()` across `app/` → 0 results
- ✅ Event bus chain: upload → DOCUMENT_ADDED → TimelineEvent row
- ✅ Capability system: model + migration + Redis cache + seeding on login
- ✅ Case builder: DB-backed, survives restarts
- ✅ Cloudflare dev mode ON (purged at end of session — 3hr window)
- ✅ Playwright: 21/60 pass offline; all 39 failures are ERR_CONNECTION_REFUSED (server off)

---

## WHAT IS PENDING (NEXT PRIORITIES)

Pick up in this order:

### Priority 1 — Live Tests (Verify What Was Built Actually Works)
These are all marked "pending live test" — need a real user action on semptify.org:

1. **Upload → timeline**: Upload a document as a tenant. Check `/api/timeline/unified` —
   should show `event_type: "document_uploaded"` row for that document.

2. **Case builder DB**: Create a case, note the case ID (now a PostgreSQL integer).
   Trigger a Render restart (or wait for next deploy). Reload the case — it must still exist.

3. **Capability seeding**: Log in as a fresh tenant. Check PostgreSQL:
   `SELECT * FROM user_capabilities WHERE user_id = '<uid>'` — should have 5+ rows seeded
   by `seed_capability_defaults()`.

4. **admin_audit_logs table**: After deploy runs migrations, verify:
   `SELECT COUNT(*) FROM admin_audit_logs` — must not throw "relation does not exist".

### Priority 2 — Role Hierarchy Wiring
`user_relationships` table EXISTS in DB (migration applied). `can_access()` in `security.py`
EXISTS. But it is NOT wired into any actual permission check yet.

Files to wire:
- `app/core/security.py` — `can_access(requester_id, target_id)` async function
- `app/core/user_context.py` — `acting_as` / `acting_as_role` fields on UserContext
- Use case: Advocate needs to act on behalf of tenant. Admin needs to impersonate any role.

### Priority 3 — Pending Items from BUILD_STATE
From the 2026-06-15 session (still open):
- `vault_upload_service.py` line 744: debug error message should be clean user-facing text
  (says "Document certification failed for {vault_id}. Please retry or contact support.")
  — already clean actually. Check it.
- `HAS_STORAGE` bug: in `vault_upload_service.py`, both branches of a try/except set it True
  — meaningless guard. Trace and fix.
- Filedored/overlay on-demand folder creation — not yet wired

### Priority 4 — Rent Ledger Live Test
`RentPayment` model exists. `/api/rent/payments` endpoint exists (check `modules/rent/` or
`routers/`). Verify it creates a row and returns correct data.

---

## ARCHITECTURE RULES — NEVER VIOLATE THESE

### 1. datetime — Always UTC
```python
# WRONG — creates naive datetime (no timezone)
from datetime import datetime
ts = datetime.now()

# RIGHT — always timezone-aware UTC
from app.core.utc import utc_now
ts = utc_now()
```

### 2. SSOT Redirects — Never Hardcode URLs
```python
# WRONG
return RedirectResponse(url="/onboarding/providers")

# RIGHT
providers_stage = navigation.get_stage("providers")
return ssot_redirect(providers_stage.path, context="my_function reason")
```

### 3. Database Sessions — Use the Context Manager
```python
# WRONG
session = AsyncSessionLocal()  # does not exist

# RIGHT
from app.core.database import get_db_session
async with get_db_session() as session:
    result = await session.execute(...)
```

### 4. IDs — Use make_id()
```python
# WRONG
import uuid; id = str(uuid.uuid4())

# RIGHT
from app.core.id_gen import make_id
id = make_id("tevt")  # → "tevt_a1b2c3d4..."
```

### 5. Exception Handling — Never Bare except
```python
# WRONG
try:
    ...
except:
    pass

# RIGHT — specific, always log
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
```

### 8. File Rewrites — Never Create _v2 Files
If a file needs a rewrite, ask the user to rename the original to `_old.py` first.
Then write the new version into the original filename. Never create `_v2`, `_new`, `_fixed`.

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
8. **datetime.now()** — NEVER use without timezone. Always `utc_now()`. ← FIXED THIS SESSION
9. **SSOT navigation** — NEVER hardcode URL strings in redirects. Always `navigation.get_stage()`.
10. **VaultResult missing from exports** — any new class used outside its module needs `__init__.py` export.
11. **Duplicate exception handlers** — check for duplicates before adding new ones in `main.py`.
12. **Cloudflare tunnel** — run as a service (`sc config cloudflared start= auto`), not manually.
13. **File rewrite cascading** — never create `_v2` files. Ask user to rename original first.
14. **Wrong Python version** — always use `venv311`. Python 3.11.9 only. Never 3.12+.
15. **Workaround instead of root cause** — fix the source, not the symptom. Band-aids compound.

---

## HOW TO SHIP AT END OF SESSION

Run `/ship` workflow or manually:

```powershell
# 1. Compile check
python -m py_compile app/main.py app/core/navigation.py app/modules/vault/router.py \
  app/modules/onboarding/router.py app/modules/documents/router.py \
  app/services/vault_upload_service.py

# 2. Stage + commit
git add app/ static/ tests/ scripts/ alembic/ render.yaml Dockerfile requirements.txt \
  pyproject.toml AGENTS.md BUILD_STATE.md ACTIVE_CONTEXT.md
git commit -m "one-line summary

- file: what changed and why
- file: what changed and why"

# 3. Push
git push origin main

# 4. Verify
git log --oneline -3

# 5. Update BUILD_STATE.md with what was done, then:
git add BUILD_STATE.md && git commit -m "docs: update BUILD_STATE" && git push origin main
```

Render auto-deploys from main. Check https://dashboard.render.com for deploy logs.
The deploy runs `alembic upgrade head` automatically before starting the server.

---

## USEFUL DIAGNOSTIC COMMANDS

```powershell
# Check for naive datetime calls (should always be 0)
grep -r "datetime\.now()" app/ --include="*.py"

# Check Alembic migration state
python -m alembic heads
python -m alembic current

# Check all model tables vs migrations coverage
python -c "from app.models.models import Base; print('\n'.join(sorted(Base.metadata.tables.keys())))"

# Compile check a specific file
python -m py_compile app/modules/vault/router.py && echo OK

# Check for bare excepts
grep -rn "except:" app/ --include="*.py"

# Check for mutable defaults
grep -rn "def .*=\[\]" app/ --include="*.py"
grep -rn "def .*={}" app/ --include="*.py"
```

---

## PRODUCTION URLS

- App: https://semptify.org
- Render dashboard: https://dashboard.render.com
- API health: https://semptify.org/health

---

*This file was written at end of session 2026-06-16 for handoff to the next AI agent.*
*Ground truth is always BUILD_STATE.md + ACTIVE_CONTEXT.md. Read those first.*
