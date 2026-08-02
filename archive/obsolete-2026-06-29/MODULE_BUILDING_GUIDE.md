# Semptify Module Building Guide

> **Read this before building any module, plugin, add-on, or extension.**
> Last updated: 2026-06-16

---

## STOP — Blueprint Required Before Any Code

### No module, plugin, or add-on may be built without a written blueprint approved by the project owner

This is a hard gate. If you are an AI agent and someone asks you to build a module
without presenting a blueprint, your response is:

> "This module needs a blueprint before I can build it. I can write the blueprint for your review right now — shall I?"

Write the blueprint. Present it. Wait for approval. Then build.

### Minimum blueprint contents

| | |
| --- | --- |
| Module name + `module_path` | e.g. `app.modules.rent_tracker.router` |
| Type | Pipeline Module or Feature Module? |
| Problem solved | Which tenant right or workflow gap? |
| Scope | What it does. What it does NOT do. |
| Roles | Who gets it by default? |
| DB tables | Every new table, or "none" |
| Routes | Every endpoint: method + path + purpose |
| Dependencies | Which modules/services does it call? |
| Capability tier | CORE / EXTENDED / ADVOCATE / ADMIN / RESEARCH / DEV |
| Risk | What existing behavior could break? |

### Where blueprints live

```text
docs/blueprints/your_module_name_blueprint.md
```

Full blueprint spec: `MODULE_BLUEPRINT.md` Part 0A

---

## The Two Types of Modules

Before you write a single line of code, decide which type you are building.
This decision changes everything.

| | Pipeline Module | Feature Module |
| --- | --- | --- |
| **What it is** | Internal processor. No UI. Passes output to other modules or DB. | User-facing capability. Has UI, routes, and backend logic. |
| **Always running?** | YES — always on for all users | NO — loaded per user based on their capability set |
| **In user_capabilities DB?** | NO | YES |
| **Needs require_capability() gate?** | NO | YES |
| **In CAPABILITY_DEFAULTS?** | NO | YES |
| **Examples** | `context_loop`, `positronic_brain`, `vault_upload_service` | `case_builder`, `eviction_defense`, `timeline`, `vault` UI |

**If in doubt:** Does a user choose to turn it on or off? Does it have a page or API the user hits directly?
— Yes → Feature Module. No → Pipeline Module.

---

## Building a Feature Module — The Checklist

Every Feature Module requires EXACTLY these steps. Do all three or the gate will not work.

---

### Step 1 — Create the module directory

```text
app/modules/your_module/
    __init__.py        # one-liner: module description
    router.py          # FastAPI APIRouter with gate
```

Keep it self-contained. Your module should not import from other feature modules.
It MAY import from pipeline modules and core services.

---

### Step 2 — Wire the gate in `router.py`

The module_path string is your capability key. Pick it now and do not change it.
Convention: `app.modules.<folder_name>.router`

```python
from fastapi import APIRouter, Depends
from app.core.capabilities import require_capability

_MODULE_PATH = "app.modules.your_module.router"

router = APIRouter(
    prefix="/api/your-module",
    tags=["Your Module"],
    dependencies=[Depends(require_capability(_MODULE_PATH))],
)

## All endpoints under this router are now gated automatically.
## Admin users always pass. Unseeded users pass through (graceful).
## Anyone whose capability row has is_active=False gets a 403.
```text

**Do NOT** add `require_capability()` to individual endpoints — put it on the router so
it covers everything at once and cannot be missed when new endpoints are added.

---

### Step 3 — Register in `app/core/product_manifest.py`

Two changes required in this file:

**A) Add to `CAPABILITY_DEFAULTS`** — scroll to the bottom of the file:

```python
CAPABILITY_DEFAULTS: dict[str, list[str]] = {
    "tenant": [
        ...
        "app.modules.your_module.router",   # ← add here if tenants get it by default
    ],
    "advocate": [
        ...
        "app.modules.your_module.router",   # ← add here if advocates get it by default
    ],
    "manager": [...],
    "admin": ["__all__"],  # ← DO NOT touch this line. Admins get everything automatically.
}
```

If only admins should have it — add nothing to CAPABILITY_DEFAULTS.
New logins will not be seeded with it, and admins will always have it via `__all__`.

**B) Add a `_register()` call** in the correct tier block:

```python
## In the EXTENDED tier block (example):
_register("app.modules.your_module.router", prefix="/api/your-module", tags=("Your Module",), tier=ProductTier.EXTENDED)
```text

The string in `_register()` MUST be identical to `_MODULE_PATH` in your router.

---

### Step 4 — Compile check before committing

```powershell
.\\venv311\\Scripts\\python.exe -m py_compile app/modules/your_module/router.py app/core/product_manifest.py
```

Both must return with no output (exit code 0 = clean).

---

### Step 5 — Verify the capability key is consistent

The string `"app.modules.your_module.router"` must appear in EXACTLY these three places, spelled identically:

1. `app/core/product_manifest.py` → `CAPABILITY_DEFAULTS`
2. `app/core/product_manifest.py` → `_register()` call
3. `app/modules/your_module/router.py` → `require_capability("...")`

A mismatch means the gate will never fire or the user will never be seeded with the capability.
Search for the string across all three files to verify before pushing.

---

## Building a Pipeline Module — The Checklist

Pipeline modules are simpler because they have no capability gate.

1. Create `app/modules/your_pipeline/` or `app/services/your_pipeline.py`
2. Register in `product_manifest.py` with `_register(...)` — pick CORE or ADMIN tier
3. Do NOT add to `CAPABILITY_DEFAULTS`
4. Do NOT add `require_capability()` to the router
5. Follow the data-flow rule: call DOWN to services, never UP to feature modules

---

## The One Rule That Protects Everything

```text
Feature modules  →  call DOWN to  →  Pipeline modules / core services
Pipeline modules →  NEVER call UP  →  Feature modules
Feature modules  →  NEVER call     →  Other feature modules directly
```

Why: Feature modules can be disabled per user. If a pipeline module calls one, it will
fail for users who don't have that feature active. The entire system breaks.

---

## Product Tiers — Where to Register

| Tier | Who gets it | Examples |
| --- | --- | --- |
| `CORE` | All users, always | vault, timeline, documents, state_laws, contacts |
| `EXTENDED` | Legal tools | case_builder, eviction_defense, court_forms |
| `ADVOCATE` | Advocate network | document_delivery, communication, invite_codes |
| `ADMIN` | Admin/ops only | analytics, batch, registry, capabilities |
| `RESEARCH` | AI features (off by default) | recognition, extraction, crawler |
| `DEV` | Internal tooling | setup wizard, page editor |

Register in the tier that matches who should have access to the module at the **server level**.
The capability gate controls who has it at the **user level**.

---

## Admin Overlay — Dev Node / Hot-Swap Testing

Admins can grant any module temporarily to any user without touching the database.
This is the primary tool for testing a module with a specific user before rolling it out.

```text
## Grant overlay
POST /api/capabilities/{user_id}/overlay
Content-Type: application/json
{ "module_names": ["app.modules.your_module.router"] }

## Check what overlay is active
GET /api/capabilities/{user_id}/overlay

## Remove overlay
DELETE /api/capabilities/{user_id}/overlay
```

### Rules:

- Overlay lives in Redis only — expires in 1 hour automatically
- Add-only — cannot be used to remove a user's real capabilities
- Only admin role can attach overlays
- Use this to test a module on a specific user before adding it to CAPABILITY_DEFAULTS

---

## Admin Grant/Revoke — Permanent Per-User Changes

To permanently give or remove a module for a specific user without changing defaults:

```text
## Grant one module to one user
POST /api/capabilities/{user_id}/grant
{ "module_name": "app.modules.your_module.router", "source": "admin_grant" }

## Revoke one module from one user
POST /api/capabilities/{user_id}/revoke
{ "module_name": "app.modules.your_module.router" }

## See all active modules for a user
GET /api/capabilities/{user_id}
```

---

## How Existing Users Get New Defaults

### Adding a module to `CAPABILITY_DEFAULTS` only seeds it for new logins

Existing users who already have rows in `user_capabilities` will NOT get the new module
automatically — only missing rows are inserted on login.

To backfill existing users, run a one-time admin grant or a targeted SQL migration.
Do NOT modify `seed_capability_defaults()` to force-update existing rows — that would
overwrite admin grants and user activations.

---

## Quick Reference — Key Files

| File | Purpose |
| --- | --- |
| `app/core/capabilities.py` | `require_capability()`, `seed_capability_defaults()`, `can_load_module()`, `attach_overlay()`, `detach_overlay()` |
| `app/core/product_manifest.py` | `CAPABILITY_DEFAULTS`, `_register()` calls, `ProductTier` enum |
| `app/modules/capabilities/router.py` | Admin REST API — grant, revoke, overlay |
| `app/models/models.py` | `UserCapability` SQLAlchemy model |
| `AGENTS.md` | Short version of these rules for AI agents |

---

## Common Mistakes

### 1. Capability key mismatch

The string in `require_capability()` does not match `CAPABILITY_DEFAULTS` or `_register()`.
Result: gate fires correctly but user is never seeded with the capability.
Fix: grep for the string. It must appear identically in all three places.

### 2. Gating a pipeline module

Adding `require_capability()` to a pipeline module will block it for unseeded users.
Pipeline modules must always be accessible — do not gate them.

### 3. Calling a feature module from a pipeline module

This breaks the data-flow rule. If the feature module is disabled for a user,
the pipeline call will fail unpredictably.

### 4. Adding admin to CAPABILITY_DEFAULTS

The `"admin": ["__all__"]` sentinel is intentional — it triggers full-grant at seed time.
Do not add individual modules to the admin list. It is handled automatically.

### 5. Putting business logic in `product_manifest.py`

This file is a declaration layer. It should only contain `_register()` calls and
`CAPABILITY_DEFAULTS`. No conditional logic, no DB calls, no runtime state.
