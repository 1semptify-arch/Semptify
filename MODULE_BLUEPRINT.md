# SEMPTIFY MODULE BLUEPRINT
**Version:** 1.0 | **Last Updated:** 2026-06-14
**Read this BEFORE building any module, plugin, or add-on for Semptify.**

---

## PART 0 — WHO WE ARE AND WHAT WE STAND FOR

**Every module, plugin, and add-on built for Semptify must honor these mandates without exception. These are not preferences. They are the foundation the entire product is built on.**

### Our Mission

Semptify exists to protect the rights of tenants facing housing insecurity, documentation challenges, and legal uncertainty. We build technology that gives tenants the same tools and information that well-funded landlords take for granted — for free, forever.

**We are on the side of tenants. Always.**
But only when tenants exercise their lawful rights. We do not support, enable, or excuse illegal behavior by any party.

### The Non-Negotiable Mandates

| Mandate | Rule |
|---|---|
| **Free Forever** | No paywalls, no subscriptions, no freemium gates. Every feature is free to every tenant. |
| **No Advertising. Ever.** | No ad networks, no sponsored content, no affiliate links, no promoted results. Not now, not later. |
| **No Tracking** | No analytics pixels, no third-party tracking scripts, no behavioral profiling, no fingerprinting. |
| **No Tenant Data Retention Beyond Need** | We do not store tenant data longer than necessary. Tenants own their data. They can export or delete it at any time. |
| **No Data Selling** | Tenant data is never sold, shared, licensed, or monetized in any form. |
| **No Hidden State** | Every action the system takes must be auditable by the tenant. No black-box processing of their documents or identity. |
| **Privacy by Design** | Documents stay in the tenant's own cloud storage (Google Drive, Dropbox, OneDrive). We never hold documents on our servers unless explicitly required for a specific operation. |
| **No Manipulation** | No dark patterns, no urgency tricks, no engagement bait, no growth-hack flows. |
| **No Surveillance Features** | No features that monitor, profile, or report on tenants' behavior — not even for "product improvement." |
| **Calm, Clear UX** | Tenants using this product are often stressed, scared, and short on time. Every UI decision must reduce friction and anxiety — not increase it. |

### What This Means for Module Builders

If you are adding a module to Semptify, you MUST ensure:

- **No external analytics calls** — do not add Google Analytics, Mixpanel, Amplitude, Segment, or any equivalent
- **No ad SDK imports** — no AdMob, no Amazon ads, no programmatic advertising of any kind
- **No third-party data brokers** — do not send tenant data to any external service without explicit tenant consent and a clear privacy disclosure
- **No retention beyond the session** — if your module processes a document for a temporary purpose, do not persist it
- **No user profiling** — do not build features that infer, score, or categorize tenants based on behavior
- **Tenant controls their data** — if your module creates records, it must support deletion by the tenant
- **Plain language** — all user-facing text must be readable by someone under stress with no legal background

### The Truth Standard

- When the law protects a tenant, say so clearly. Do not soften it.
- When a landlord violates the law, name it plainly. Do not excuse it.
- Do not produce content that hedges legal facts into uselessness.
- Do not treat housing as a "both sides" issue when the law is clear.
- Build for facts, records, chronology, and evidence — never emotion or assumption.

### The Product Decision Filter

When choosing between two approaches, always prefer the one that better serves:

1. Rights protection
2. Evidence integrity
3. Tenant control
4. Clarity under stress
5. Privacy

**Reject any approach that primarily serves:** monetization, advertising, engagement metrics, hidden data collection, or complexity without workflow benefit.

---

## PART 1 — THE THREE TYPES OF EXTENSIONS

| Type | What It Is | Example |
|---|---|---|
| **Module** | A self-contained feature with its own DB tables, routes, and UI | FEMS, MNDES, Documents |
| **Plugin** | A drop-in enhancement that hooks into existing modules | AI classifier, PDF watermarker |
| **Add-on** | A lightweight router with no DB tables | State laws, free API pack |

All three follow the **same registration process**. The only difference is scope.

---

## PART 2 — THE GOLDEN RULES (Non-Negotiable)

1. **NEVER add `app.include_router()` directly to `main.py`** — use `product_manifest.py`
2. **NEVER create your own SQLAlchemy `Base`** — use `app.core.database.Base`
3. **NEVER hardcode config values** — read from `app.core.config.get_settings()`
4. **NEVER import from `app.routers.*`** — all modules live in `app.modules.*`
5. **ALWAYS mark new modules `optional=True`** — so startup survives if your module fails
6. **ALWAYS provide `GET /api/{your_module}/health`** — returns `{"status": "healthy"}`
7. **ALWAYS use `datetime.now(timezone.utc)`** — never bare `datetime.now()`
8. **ALWAYS use specific exception types** — never bare `except:`
9. **Python 3.11.9 ONLY** — no dependency that requires 3.12+
10. **All new DB tables go through Alembic** — never rely on `create_all()` alone

---

## PART 3 — REQUIRED FOLDER STRUCTURE

```
app/modules/{your_module}/
    __init__.py          ← exports router + models
    config.py            ← module-level env vars and constants
    models.py            ← SQLAlchemy ORM models (use Base from database.py)
    router.py            ← FastAPI APIRouter with all endpoints
    service.py           ← business logic (optional but recommended)
    schemas.py           ← Pydantic request/response models (optional)
```

Minimum required files: `__init__.py`, `router.py`
For any module with DB tables, also required: `models.py`

---

## PART 4 — STEP BY STEP IMPLEMENTATION

### Step 1 — Create the folder

```
app/modules/your_module/
```

### Step 2 — Write `config.py`

```python
"""your_module configuration."""
import os
from pathlib import Path

YOUR_MODULE_ENABLED = os.getenv("YOUR_MODULE_ENABLED", "true").lower() == "true"
YOUR_MODULE_PREFIX = "/api/your_module"
```

### Step 3 — Write `models.py` (skip if no DB tables needed)

```python
"""your_module SQLAlchemy models."""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text
from app.core.database import Base          # ← ALWAYS use this Base


class YourRecord(Base):
    __tablename__ = "your_module_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### Step 4 — Write `router.py`

```python
"""your_module FastAPI router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.your_module.models import YourRecord

router = APIRouter(prefix="/api/your_module", tags=["Your Module"])


@router.get("/health")
async def health():
    return {"status": "healthy", "module": "your_module", "version": "1.0.0"}


@router.get("/records")
async def list_records(db: AsyncSession = Depends(get_db)):
    records = (await db.execute(select(YourRecord))).scalars().all()
    return [{"id": r.id, "title": r.title} for r in records]
```

### Step 5 — Write `__init__.py`

```python
"""your_module — brief description."""
from app.modules.your_module.router import router
from app.modules.your_module.models import YourRecord

__all__ = ["router", "YourRecord"]
```

### Step 6 — Register models with the database

Open `app/core/database.py` and add your import in the model registration block at the bottom:

```python
# Register your_module models with SQLAlchemy Base
try:
    import app.modules.your_module.models  # noqa: F401
except ImportError:
    pass
```

### Step 7 — Register the module in the manifest

Open `app/core/product_manifest.py` and add ONE `_register()` call in the correct tier:

```python
# your_module — brief description
_register(
    "app.modules.your_module.router",
    tags=("Your Module",),
    prefix="",
    optional=True,
    tier=ProductTier.EXTENDED,          # choose the right tier — see Part 5
    log_message="your_module router loaded — active at /api/your_module",
)
```

**That is ALL you touch in `main.py` or `product_manifest.py`.** Nothing else.

### Step 8 — Create the Alembic migration (required if you have DB tables)

Create a new file: `alembic/versions/YYYYMMDD_add_your_module_tables.py`

```python
"""Add your_module tables

Revision ID: YYYYMMDD_add_your_module_tables
Revises: <previous_revision_id>           ← get this from: alembic heads
Create Date: YYYY-MM-DD 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'YYYYMMDD_add_your_module_tables'
down_revision = '<previous_revision_id>'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'your_module_records',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_your_module_records_id', 'your_module_records', ['id'])


def downgrade() -> None:
    op.drop_table('your_module_records')
```

Then run:
```powershell
.\venv311\Scripts\Activate.ps1
python -m alembic upgrade head
```

### Step 9 — Verify it compiled and loaded

```powershell
# Compile check
python -m py_compile app/modules/your_module/__init__.py app/modules/your_module/router.py

# Start server and look for your log message
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Look for: "your_module router loaded — active at /api/your_module"

# Hit the health endpoint
Invoke-RestMethod http://localhost:8000/api/your_module/health
```

### Step 10 — Ship it

```powershell
git add app/modules/your_module/ app/core/database.py app/core/product_manifest.py alembic/versions/
git commit -m "feat: add your_module module"
git push origin main
```

---

## PART 5 — WHICH TIER TO USE

| Tier | Use When | Default State |
|---|---|---|
| `ProductTier.CORE` | Essential — app breaks without it | **Always active** |
| `ProductTier.EXTENDED` | Legal tools, case management, evidence | Active (all tiers enabled) |
| `ProductTier.ADVOCATE` | Outreach, communications, delivery | Active (all tiers enabled) |
| `ProductTier.ADMIN` | Analytics, dashboards, admin tools | Active (all tiers enabled) |
| `ProductTier.RESEARCH` | AI, ML, experimental features | Active (all tiers enabled) |
| `ProductTier.DEV` | Dev tools, testing, page editor | **Always active** |

**Current state:** All 6 tiers are active in production. Register new modules in the tier that best fits their purpose.

---

## PART 6 — OPTIONAL: ADD A UI PAGE

If your module needs a frontend page:

1. Create `static/your_module/index.html`
2. Add a route in `router.py`:

```python
from fastapi.responses import FileResponse

@router.get("/ui", response_class=FileResponse)
async def ui_page():
    return FileResponse("static/your_module/index.html")
```

3. Link from the tenant nav if appropriate (update `static/components/nav.html`)

---

## PART 7 — OPTIONAL: LINK TO SEMPTIFY USER ACCOUNTS

If your module needs to know which tenant owns a record, add a `user_id` column:

```python
from sqlalchemy import Column, String
# In your model:
user_id = Column(String(100), nullable=True, index=True)
```

Retrieve the current user in a route:

```python
from fastapi import Request
from app.core.cookie_auth import extract_user_id

@router.get("/my-records")
async def my_records(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = extract_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    records = (await db.execute(
        select(YourRecord).where(YourRecord.user_id == user_id)
    )).scalars().all()
    return records
```

---

## PART 8 — COMMON MISTAKES (DO NOT REPEAT)

| Mistake | Consequence | Fix |
|---|---|---|
| Adding `include_router()` to `main.py` | Breaks manifest system, AI agents repeat mistake | Use `_register()` in `product_manifest.py` |
| Creating own `Base = declarative_base()` | Tables invisible to Alembic, migrations break | Always import `Base` from `app.core.database` |
| Using `datetime.now()` without UTC | Token expiry bugs, timezone inconsistencies | Use `datetime.now(timezone.utc)` |
| Not marking module `optional=True` | One bad import kills entire server startup | Always set `optional=True` |
| Putting secrets in code | Security breach | Read from `get_settings()` or `os.getenv()` |
| Bare `except:` | Silent failures, impossible to debug | Use `except SpecificException` |
| Creating `_v2` or `_new` file variants | Cascading import breaks across codebase | Rename original first, write into original name |
| Skipping Alembic migration | Tables missing in production on Render | Always write a migration file |

---

## PART 9 — QUICK REFERENCE CHECKLIST

Before opening a PR or shipping, verify every item:

- [ ] Module folder exists at `app/modules/{name}/`
- [ ] `__init__.py` exports `router` and any models
- [ ] `router.py` has `GET /api/{name}/health` returning `{"status": "healthy"}`
- [ ] `models.py` uses `from app.core.database import Base`
- [ ] Models registered via import in `app/core/database.py`
- [ ] One `_register()` call added to `app/core/product_manifest.py`
- [ ] Alembic migration created and run (`alembic upgrade head`)
- [ ] All files compile: `python -m py_compile app/modules/{name}/*.py`
- [ ] Server starts and log shows module loaded
- [ ] Health endpoint returns 200
- [ ] No hardcoded secrets, URLs, or Python version assumptions
- [ ] `BUILD_STATE.md` updated

---

## PART 10 — KEY FILE LOCATIONS

| File | Purpose |
|---|---|
| `app/core/product_manifest.py` | **THE manifest — register all modules here** |
| `app/core/database.py` | Base class + DB session — import `Base` and `get_db` from here |
| `app/core/config.py` | All config — use `get_settings()` |
| `app/core/cookie_auth.py` | Auth — use `extract_user_id(request)` |
| `app/core/navigation.py` | SSOT routing — use `navigation.get_stage()` for redirects |
| `alembic/versions/` | All DB migrations live here |
| `app/modules/fems/` | Reference implementation — copy this structure |
| `SEMPTIFY_SYSTEM_MANIFEST.md` | Living list of all active/disabled modules |
| `BUILD_STATE.md` | What was last shipped and what is pending |
