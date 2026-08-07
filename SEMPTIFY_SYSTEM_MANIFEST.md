# SEMPTIFY SYSTEM MANIFEST
**Version:** 5.0.0 | **Last Updated:** 2026-06-14 | **Location:** `C:\Semptify\Semptify-FastAPI\`

This is the FIRST file any AI or developer must read before touching Semptify. It defines what is active, what is disabled, the rules for adding modules, and the complete session context.

---

## PART 1 — PROJECT IDENTITY

| Item | Value |
|---|---|
| App Name | Semptify |
| Version | 5.0.0 |
| Mission | Tenant rights protection platform (non-profit) |
| Root Path | `C:\Semptify\Semptify-FastAPI\` |
| Entry Point | `app/main.py` (DO NOT add routers here directly) |
| Manifest | `app/core/product_manifest.py` (SINGLE SOURCE OF TRUTH) |
| Python | **3.11.9 ONLY — hard enforced, kills server if wrong** |
| Venv | `venv311\Scripts\Activate.ps1` |
| Database (dev) | SQLite — `semptify.db` |
| Database (prod) | PostgreSQL via `DATABASE_URL` in `.env` |
| DB ORM | SQLAlchemy async (`app.core.database`) |
| DB Base Class | `app.core.database.Base` — ALL models must use this |
| Config | `app.core.config.get_settings()` |
| Auth | Cookie-based via `app.core.cookie_auth.extract_user_id` |
| Templates | Jinja2 at `app/templates/` |
| Static Files | `static/` |
| Uploads | `uploads/vault/` |

---

## PART 2 — THE GOLDEN RULE

**Never add `app.include_router()` directly to `main.py`.**

All modules are declared in `app/core/product_manifest.py` and loaded via:
```python
register_tiers(fastapi_app, ProductTier.CORE, ProductTier.DEV)
```

To add a new module — only 3 steps:
1. Create files in `app/modules/your_module/`
2. Add one `_register(...)` line to `product_manifest.py`
3. If needed, add the tier to the `register_tiers()` call in `main.py`

**Do not touch anything else.**

---

## PART 3 — PRODUCT TIERS

| Tier | Status | Purpose |
|---|---|---|
| `CORE` | ✅ **ACTIVE** | Tenant rights essentials — always on |
| `EXTENDED` | ❌ Disabled | Legal tools, eviction defense, court forms |
| `ADVOCATE` | ❌ Disabled | Document delivery, collaboration |
| `ADMIN` | ❌ Disabled | Analytics, dashboards, batch ops |
| `RESEARCH` | ❌ Disabled | AI intelligence, brain, mesh network |
| `DEV` | ✅ **ACTIVE** | Internal dev tools |

---

## PART 4 — ACTIVE MODULES (CORE + DEV tiers)

### CORE — Currently Running

| Module Path | Endpoint Prefix | Required | Purpose |
|---|---|---|---|
| `app.modules.health.router` | `/health` | **YES** | Health checks |
| `app.core.versioning` | `/version` | No | Version info |
| `app.modules.preamble.router` | `/` | No | Landing page |
| `app.modules.risc.router` | `/risc` | No | Risk assessment |
| `app.modules.role_ui.router` | `/` | No | Role-based routing |
| `app.modules.storage.router` | `/storage` | No | OAuth storage auth |
| `app.modules.auth.router` | `/api/auth` | No | Auth status |
| `app.modules.onboarding.reconnect` | `/storage/reconnect` | No | Reconnect flow |
| `app.modules.documents.router` | `/documents` | No | Document upload/retrieval |
| `app.modules.vault.router` | `/api/vault` | No | Vault access |
| `app.modules.vault_engine.router` | `/api/vault-engine` | No | Vault access control |
| `app.modules.timeline.router` | `/api/timeline` | No | Event timeline |
| `app.modules.briefcase.router` | `/briefcase` | No | Tenant briefcase |
| `app.modules.workflow.router` | `/workflow` | No | SSOT workflow engine |
| `app.modules.workflow_validator.router` | `/admin` | No | Workflow validation |
| `app.modules.state_laws.router` | `/state-laws` | No | State housing laws |
| `app.modules.law_library.router` | `/law-library` | No | Law reference library |
| `app.modules.contacts.router` | `/contacts` | No | Contact manager |
| `app.modules.public_forms.router` | `/forms` | No | Public forms |
| `app.modules.search.router` | `/api/search` | No | Global search |
| `app.modules.pdf_tools.router` | `/pdf` | No | PDF tools |
| `app.modules.preview.router` | `/api/preview` | No | Document preview |
| `app.modules.document_converter.router` | `/convert` | No | Doc conversion |
| `app.modules.legal_analysis.router` | `/legal-analysis` | No | Legal analysis |
| `app.modules.websocket.router` | `/ws` | No | Real-time events |
| `app.modules.free_api.router` | `/free-api` | No | Free public APIs |
| `app.modules.plugins.router` | `/plugins` | No | Plugin system |
| `app.modules.components.router` | `/components` | No | UI components |
| `app.modules.core_system.router` | `/core` | No | Core infrastructure |
| `app.modules.security.router` | `/api/security` | No | 2FA / session mgmt |
| `app.modules.mndes.router` | `/mndes` | **YES** | MN court exhibit system |

### DEV — Currently Running

| Module Path | Endpoint Prefix | Purpose |
|---|---|---|
| `app.modules.setup.router` | `/api/setup` | Setup wizard |
| `app.modules.page_index.router` | `/page-index` | Page index DB |
| `app.modules.page_editor.router` | `/page-editor` | Template editor |
| `app.modules.development.router` | `/dev` | Dev tools |
| `app.modules.export_import.router` | `/api/export-import` | Data export/import |
| `app.modules.testing.router` | `/api/testing` | Testing framework |
| `app.modules.documentation.router` | `/api/docs` | Developer portal |

---

## PART 5 — DISABLED MODULES (Do NOT re-enable without explicit approval)

### Services Intentionally Disabled in `main.py` Stage 5

| Service | Reason |
|---|---|
| Positronic Brain | Memory hog |
| Module Hub & Mesh | Memory hog |
| Location Service | Not needed for MVP |
| Complaint Wizard mesh registration | Not needed for MVP |
| Plugin Manager auto-discovery | Not needed for MVP |

### EXTENDED Tier (disabled, not broken — re-enable by adding `ProductTier.EXTENDED` to `register_tiers`)

`eviction_defense`, `zoom_court`, `zoom_court_prep`, `court_forms`, `court_packet`, `legal_filing`, `legal_trails`, `tenant_defense`, `intake`, `guided_intake`, `case_builder`, `progress`, `actions`, `plan_maker`, `tools_api`, `complaints`, `housing_accountability`, `role_upgrade`

### RESEARCH Tier (disabled — memory heavy, AI-dependent)

`recognition`, `extraction`, `crawler`, `research`, `form_data`, `overlays`, `unified_overlays`, `vault_all_in_one`, `cloud_sync`, `brain`, `auto_mode`, `emotion`, `positronic_mesh`, `mesh_network`, `module_hub`, `functionx`, `funding_search`, `hud_funding`, `location`, `campaign`, `public_exposure`, `fraud_exposure`, `litigation_intelligence`

---

## PART 6 — HOW TO ADD A NEW MODULE (Exact Steps)

### Step 1 — Create module folder
```
app/modules/your_module/
├── __init__.py        # exports router + models
├── router.py          # FastAPI APIRouter
├── models.py          # SQLAlchemy models using Semptify Base
├── config.py          # reads from .env via get_settings()
└── README.md          # what your module does
```

### Step 2 — Minimum required content for `router.py`
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/your_module", tags=["Your Module"])


@router.get("/health")
async def health():
    return {"status": "healthy", "module": "your_module"}
```

### Step 3 — Minimum required content for `models.py`
```python
from app.core.database import Base
from sqlalchemy import Column, Integer, String
# Use Base from Semptify — never create a new Base


class YourModel(Base):
    __tablename__ = "your_module_table"
    id = Column(Integer, primary_key=True)
```

### Step 4 — Register in `app/core/product_manifest.py`
```python
# Add under the appropriate tier section:
_register(
    "app.modules.your_module.router",
    tags=("Your Module",),
    tier=ProductTier.EXTENDED,  # or CORE, ADMIN, etc.
    optional=True,  # ALWAYS True for new modules
    log_message="Your Module loaded",
)
```

### Step 5 — Enable the tier in `main.py` if not already active
```python
# Find this line in main.py and add your tier:
register_tiers(fastapi_app, ProductTier.CORE, ProductTier.DEV, ProductTier.EXTENDED)
```

### Step 6 — Register models with SQLAlchemy (in `app/core/database.py`)
```python
# Add near other model imports:
import app.modules.your_module.models  # noqa: F401
```

---

## PART 7 — FEMS MODULE PLAN

FEMS (Forensic Evidence Management System) is the next module to be integrated.

| Item | Value |
|---|---|
| FEMS Source | `c:\REPOs\PPPP\` |
| Target Path | `C:\Semptify\Semptify-FastAPI\app\modules\fems\` |
| Tier | `EXTENDED` |
| Endpoints | `/api/fems/health`, `/api/fems/upload`, `/api/fems/search`, `/api/fems/documents`, `/api/fems/quarantine`, `/api/fems/stats` |
| DB Adapter | Must use SQLAlchemy async (not psycopg2) |
| Status | Planned — not yet integrated |

FEMS provides: file deduplication, OCR text extraction, phone number extraction, carrier log CSV parsing, SMS import, and forensic evidence search — feeding Semptify's EXTENDED legal modules.

---

## PART 8 — MODULE DEVELOPER RULES (For Any AI or Human)

1. **Read this file first** before any session
2. **`product_manifest.py` is the only place** to register routers
3. **Never use `psycopg2`** — use SQLAlchemy async
4. **Never create a new `Base`** — import from `app.core.database`
5. **Never hardcode config** — use `get_settings()` or `.env`
6. **`optional=True` on all new modules** — Semptify must start even if module fails
7. **Python 3.11.9 only** — do not use 3.10, 3.12, or any other version
8. **Health endpoint required** — every module needs `GET /api/{name}/health`
9. **No circular imports** — modules must not import from each other
10. **Test in venv311** — always activate `venv311` before running

---

## PART 9 — START / STOP COMMANDS

```powershell
# Activate environment
cd "C:\Semptify\Semptify-FastAPI"
.\venv311\Scripts\Activate.ps1

# Start server (dev)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or use batch script
.\start.bat

# Verify health
Invoke-RestMethod http://localhost:8000/health

# Check FEMS (after integration)
Invoke-RestMethod http://localhost:8000/api/fems/health
```

---

## PART 10 — CONTEXT TRANSFER NOTES

This document was created during a session that:
- Audited the full Semptify system structure
- Identified `product_manifest.py` as the real routing authority
- Planned FEMS as a Semptify EXTENDED module
- Created the Module Developer Kit plan
- Established rules to prevent AIs from breaking `main.py`

**Next steps when resuming:**
1. Build `app/modules/fems/` files
2. Register FEMS in `product_manifest.py`
3. Enable `ProductTier.EXTENDED` in `main.py`
4. Verify `/api/fems/health` returns 200
