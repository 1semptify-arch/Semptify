# Semptify Developer Onboarding Manual
**Version 1.0 — June 2026**
**For external contributors and module developers**

---

> This document tells you everything you need to know before writing a single line of code for Semptify.
> Read it in order. Do not skip sections.

---

## 1. Who We Are and What We Stand For

Semptify exists to protect the rights of tenants facing housing insecurity.
We give tenants the same tools that well-funded landlords take for granted — for free, forever.

**We are on the side of tenants. Always.**

### The Non-Negotiables

These are not preferences. Every module, plugin, and add-on must honor them without exception.

| Mandate | Rule |
|---|---|
| **Free Forever** | No paywalls, no subscriptions, no freemium gates. Every feature is free. |
| **No Advertising. Ever.** | No ad networks, no sponsored content, no affiliate links. Not now, not later. |
| **No Tracking** | No analytics pixels, no third-party tracking scripts, no behavioral profiling. |
| **Privacy by Design** | Documents stay in the tenant's own cloud storage. We never hold documents on our servers unless a specific operation requires it. |
| **No Data Selling** | Tenant data is never sold, shared, licensed, or monetized in any form. |
| **No Hidden State** | Every action the system takes must be auditable by the tenant. |
| **No Manipulation** | No dark patterns, no urgency tricks, no engagement bait, no growth-hack flows. |
| **Calm, Clear UX** | Tenants are often stressed, scared, and short on time. Every UI decision must reduce friction — not increase it. |

### What This Means for You as a Developer

- **No external analytics calls** — do not add Google Analytics, Mixpanel, Amplitude, or any equivalent
- **No ad SDK imports** — no advertising SDKs of any kind
- **No third-party data brokers** — do not send tenant data to any external service without explicit consent
- **Plain language** — all user-facing text must be readable by someone under stress with no legal background
- **Tenant controls their data** — if your module creates records, it must support deletion by the tenant

### The Truth Standard

- When the law protects a tenant, say so clearly. Do not soften it.
- When a landlord violates the law, name it plainly. Do not excuse it.
- Build for facts, records, chronology, and evidence — never emotion or assumption.

---

## 2. Before You Write a Single Line of Code — The Blueprint Rule

**No module, plugin, or add-on may be built without a written blueprint approved by the project owner first.**

This is a hard gate. Code written before approval will be removed.

### What Your Blueprint Must Cover

Write a plain Markdown document covering these sections:

| Section | What to answer |
|---|---|
| **Module name** | What is it called? What is the dotted path? (e.g. `app.modules.rent_tracker.router`) |
| **Type** | Pipeline Module or Feature Module? (explained in Section 4) |
| **Problem it solves** | Which tenant right or workflow gap does this address? |
| **Scope** | What does it do? What does it explicitly NOT do? |
| **User-facing or internal?** | Does a tenant interact with it directly? |
| **Roles** | Which roles get it by default? (tenant / advocate / manager / admin) |
| **DB tables** | List every new table. If none, write "none". |
| **Routes** | Every API endpoint: method + path + one-line purpose |
| **Dependencies** | Which existing modules or services does it call? |
| **Data flow** | Where does data come from? Where does it go? |
| **What it does NOT touch** | Explicitly list modules, tables, or routes it does not affect |
| **Capability tier** | CORE / EXTENDED / ADVOCATE / ADMIN / RESEARCH / DEV |
| **Risk** | What could go wrong? What existing behavior could break? |

### Where to Put It

Save your blueprint as:
```
docs/blueprints/your_module_name_blueprint.md
```

Add a status line at the top:
```
Status: DRAFT — pending approval
```

### The Approval Process

1. Write the blueprint
2. Send it to the project owner for review
3. Wait for explicit approval — "yes build it" counts
4. Only then open any source files and write code
5. When shipped, update status to `BUILT — shipped in commit <hash>`

**A 10-minute blueprint prevents a 3-session cleanup. Do not skip this step.**

---

## 3. Technical Requirements — Non-Negotiable

### Python Version

**Semptify requires Python 3.11.9. This is a hard mandate.**

- All code must target Python 3.11.9
- Do NOT introduce any dependency that requires Python 3.12, 3.13, or later
- Before adding any new package, confirm it supports Python 3.11.9
- If a library only works on 3.12+, reject it and find an alternative

### Environment Setup (Local Development)

```powershell
# Activate the correct virtual environment
.\\venv311\\Scripts\\Activate.ps1

# Verify Python version — must show 3.11.x
python --version

# Run the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### The Golden Rules

1. **NEVER add `app.include_router()` directly to `main.py`** — use `product_manifest.py`
2. **NEVER create your own SQLAlchemy `Base`** — use `from app.core.database import Base`
3. **NEVER hardcode config values** — read from `app.core.config.get_settings()`
4. **NEVER import from `app.routers.*`** — all modules live in `app.modules.*`
5. **ALWAYS mark new modules `optional=True`** — so startup survives if your module fails
6. **ALWAYS provide `GET /api/{your_module}/health`** — returns `{"status": "healthy"}`
7. **ALWAYS use `utc_now()` from `app.core.utc`** — never bare `datetime.now()`
8. **ALWAYS use specific exception types** — never bare `except:`
9. **All new DB tables go through Alembic** — never rely on `create_all()` alone
10. **NEVER create `_v2`, `_new`, or `_fixed` file variants** — see Section 8 on the swap protocol

---

## 4. The Two Types of Modules

Before you write anything, decide which type you are building. This decision changes everything.

| | Pipeline Module | Feature Module |
|---|---|---|
| **What it is** | Internal processor. No UI. Passes output to other modules or the database. | User-facing capability. Has UI, routes, and backend logic. |
| **Always running?** | YES — always on for all users | NO — loaded per user based on their capability set |
| **Needs a capability gate?** | NO | YES |
| **In role defaults?** | NO | YES |
| **Examples** | `context_loop`, `positronic_brain`, vault upload service | `case_builder`, `eviction_defense`, `timeline`, vault UI |

**Decision test:** Does a user choose to turn it on or off? Does it have a page or API the user hits directly?
- Yes → Feature Module
- No → Pipeline Module

### The One Rule That Protects Everything

```
Feature modules  →  call DOWN to  →  Pipeline modules / core services
Pipeline modules →  NEVER call UP  →  Feature modules
Feature modules  →  NEVER call     →  Other feature modules directly
```

Why this matters: Feature modules can be disabled per user. If a pipeline module calls a feature module,
it will silently fail for users who don't have that feature. The entire system breaks.

---

## 5. Building a Feature Module — Step by Step

### Step 1 — Write and get the blueprint approved (Section 2)

### Step 2 — Create the module folder

```
app/modules/your_module/
    __init__.py        ← one-liner: module description + exports
    router.py          ← FastAPI APIRouter with capability gate
    models.py          ← SQLAlchemy models (only if you have DB tables)
    service.py         ← business logic (recommended but optional)
    schemas.py         ← Pydantic request/response models (optional)
```

Minimum required files: `__init__.py` and `router.py`.
If you have DB tables, also required: `models.py`.

### Step 3 — Wire the capability gate in `router.py`

Every Feature Module must have a capability gate. This is the mechanism that controls
which users can access your module. One line does it all:

```python
from fastapi import APIRouter, Depends
from app.core.capabilities import require_capability

# This string is your capability key. Pick it now. Never change it.
# Convention: app.modules.<folder_name>.router
_MODULE_PATH = "app.modules.your_module.router"

router = APIRouter(
    prefix="/api/your-module",
    tags=["Your Module"],
    dependencies=[Depends(require_capability(_MODULE_PATH))],
)


@router.get("/health")
async def health():
    return {"status": "healthy", "module": "your_module"}
```

The gate automatically handles:
- Admin users always pass through (no gate for admins)
- Users not yet seeded pass through gracefully (no lockouts)
- Users whose capability is inactive get a clean 403 response
- Admin overlays (temporary grants) always win

### Step 4 — Write `models.py` (skip if no DB tables)

```python
"""your_module SQLAlchemy models."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from app.core.database import Base  # ALWAYS use this Base
from app.core.utc import utc_now  # ALWAYS use this for timestamps


class YourRecord(Base):
    __tablename__ = "your_module_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(256), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
```

### Step 5 — Register models in `app/core/database.py`

Find the model registration block at the bottom of `database.py` and add:

```python
try:
    import app.modules.your_module.models  # noqa: F401
except ImportError:
    pass
```

### Step 6 — Register in `app/core/product_manifest.py` — TWO changes required

**Change A:** Add to `CAPABILITY_DEFAULTS` (scroll to the bottom of the file):

```python
CAPABILITY_DEFAULTS: dict[str, list[str]] = {
    "tenant": [
        ...
        "app.modules.your_module.router",   # add if tenants get it by default
    ],
    "advocate": [
        ...
        "app.modules.your_module.router",   # add if advocates get it by default
    ],
    # DO NOT touch "admin": ["__all__"] — admins get everything automatically
}
```

**Change B:** Add a `_register()` call in the correct tier block:

```python
_register(
    "app.modules.your_module.router",
    prefix="",
    tags=("Your Module",),
    optional=True,
    tier=ProductTier.EXTENDED,  # choose the right tier
    log_message="your_module router loaded",
)
```

**Critical:** The string `"app.modules.your_module.router"` must be identical in:
1. `require_capability(...)` in your `router.py`
2. `CAPABILITY_DEFAULTS` in `product_manifest.py`
3. `_register(...)` in `product_manifest.py`

A mismatch means the gate fires but users are never seeded, or users are seeded but the gate never fires.

### Step 7 — Create the Alembic migration (required if you have DB tables)

```powershell
# Generate the migration
python -m alembic revision --autogenerate -m "add_your_module_tables"
```

Then open the generated file in `alembic/versions/` and **remove all changes that are not your new table**.
Autogenerate picks up schema drift from other tables — keep only your `create_table` call.

Run it:
```powershell
python -m alembic upgrade head
```

### Step 8 — Compile check before committing

```powershell
.\\venv311\\Scripts\\python.exe -m py_compile app/modules/your_module/router.py app/core/product_manifest.py
```

Both must return with no output (exit code 0 = clean).

### Step 9 — Ship it

```powershell
git add app/modules/your_module/ app/core/product_manifest.py alembic/versions/
git commit -m "feat: add your_module — brief description"
git push origin main
```

---

## 6. Building a Pipeline Module

Pipeline modules are simpler — no capability gate, no defaults.

1. Get blueprint approved (Section 2)
2. Create `app/modules/your_pipeline/` or `app/services/your_pipeline.py`
3. Register in `product_manifest.py` with `_register(...)` — CORE or ADMIN tier
4. Do NOT add to `CAPABILITY_DEFAULTS`
5. Do NOT add `require_capability()` to the router
6. Follow the data-flow rule: call DOWN to services, never UP to feature modules

---

## 7. Which Product Tier to Register In

| Tier | Use When |
|---|---|
| `CORE` | Essential — the app is broken without it |
| `EXTENDED` | Legal tools — case management, eviction defense, court forms |
| `ADVOCATE` | Advocate network — document delivery, collaboration |
| `ADMIN` | Dashboards, analytics, admin tools |
| `RESEARCH` | AI features, experimental, off by default |
| `DEV` | Internal tooling, development only |

---

## 8. The File Swap Protocol — Never Create `_v2` Files

If you need to rewrite a file that already exists:

**NEVER do this:**
```
vault_upload_service.py       ← broken original, left in place
vault_upload_service_v2.py    ← your rewrite
```
This breaks every import across the codebase. You will spend hours chasing cascading failures.

**Always do this:**
1. Ask the project owner to rename the original to `your_file_old.py` (one filesystem rename)
2. Write your clean version into the original filename `your_file.py`
3. Every import everywhere still works — nothing else changes
4. The `_old` file is the rollback. Delete it once verified.

---

## 9. The Admin Overlay — Testing Your Module

Before rolling a module out to all users, you can test it with a specific user
without touching the database:

```
POST /api/capabilities/{user_id}/overlay
Content-Type: application/json
{ "module_names": ["app.modules.your_module.router"] }
```

This temporarily grants the user access to your module for 1 hour.
It lives in Redis only — expires automatically, no DB change, no effect on anyone else.

To remove it:
```
DELETE /api/capabilities/{user_id}/overlay
```

To permanently grant a module to a specific user:
```
POST /api/capabilities/{user_id}/grant
{ "module_name": "app.modules.your_module.router", "source": "admin_grant" }
```

---

## 10. Pre-Ship Checklist

Before opening a pull request or pushing to main, verify every item:

- [ ] Blueprint written and approved by project owner
- [ ] Blueprint saved to `docs/blueprints/your_module_name_blueprint.md` with status `BUILT`
- [ ] Module folder at `app/modules/{name}/`
- [ ] `__init__.py` exports `router` and any models
- [ ] `router.py` has `GET /api/{name}/health` returning `{"status": "healthy"}`
- [ ] `router.py` has `require_capability(...)` as a router-level dependency (Feature Modules only)
- [ ] `models.py` uses `from app.core.database import Base`
- [ ] Models registered via import in `app/core/database.py`
- [ ] `CAPABILITY_DEFAULTS` updated in `product_manifest.py` (Feature Modules only)
- [ ] One `_register()` call added to `product_manifest.py`
- [ ] Capability key string is identical in all three locations
- [ ] Alembic migration written and run (`alembic upgrade head`)
- [ ] All files compile: `python -m py_compile app/modules/{name}/*.py`
- [ ] No hardcoded secrets, URLs, or Python version assumptions
- [ ] No bare `except:` blocks
- [ ] No `datetime.now()` without timezone (use `utc_now()`)
- [ ] `BUILD_STATE.md` updated with what was shipped

---

## 11. Key Files — Where Everything Lives

| File | What it is |
|---|---|
| `MODULE_BLUEPRINT.md` | Full module spec, golden rules, and implementation guide |
| `MODULE_BUILDING_GUIDE.md` | Capability system rules for new modules |
| `AGENTS.md` | Rules for AI coding assistants working in this repo |
| `app/core/product_manifest.py` | **The manifest — register ALL modules here** |
| `app/core/capabilities.py` | `require_capability()`, `seed_capability_defaults()`, overlay functions |
| `app/core/database.py` | `Base` class and `get_db` session — import from here |
| `app/core/config.py` | All config — use `get_settings()` |
| `app/core/utc.py` | `utc_now()` — always use this for timestamps |
| `app/modules/fems/` | Reference implementation — copy this structure |
| `alembic/versions/` | All DB migrations live here |
| `docs/blueprints/` | All approved module blueprints live here |
| `BUILD_STATE.md` | What was last shipped and what is pending |
| `ACTIVE_CONTEXT.md` | What is being worked on right now |

---

## 12. Common Mistakes — Do Not Repeat These

| Mistake | Consequence | Fix |
|---|---|---|
| Building without a blueprint | Scope creep, undefined dependencies, capability gate never wired | Write the blueprint. Get approval. Then build. |
| Adding `include_router()` to `main.py` | Breaks the manifest system | Use `_register()` in `product_manifest.py` |
| Creating own `Base = declarative_base()` | Tables invisible to Alembic | Always import `Base` from `app.core.database` |
| Using `datetime.now()` without UTC | Token expiry bugs, timezone inconsistencies | Use `utc_now()` from `app.core.utc` |
| Not marking module `optional=True` | One bad import kills the entire server | Always set `optional=True` in `_register()` |
| Creating `_v2` or `_new` file variants | Cascading import breaks across the codebase | Use the swap protocol (Section 8) |
| Skipping Alembic migration | Tables missing in production | Always write a migration file |
| Capability key mismatch | Gate fires but user never seeded, or vice versa | Same string in all three locations |
| Gating a pipeline module | Blocks it for unseeded users | Pipeline modules are exempt from gating |
| Bare `except:` blocks | Silent failures, impossible to debug | Use `except SpecificException` |
| Calling a feature module from a pipeline module | Breaks for users without that feature | Fix the data-flow. Pipeline calls down only. |

---

*Semptify Developer Onboarding Manual — v1.0 — June 2026*
*For questions, contact the project owner before writing code.*
