# Semptify → SDK Modules Conversion Plan

## Status: ✅ COMPLETE (2026-05-17)

All routers converted. 89 SDK modules created. Zero `app.routers` references remain.

## Current State

The app is now a **modular FastAPI application** with:
- **89 SDK modules** in `app/modules/` (each with `router.py`, `manifest.py`, `__init__.py`)
- **65+ services** in `app/services/` (scattered, next phase: migrate into modules)
- **6 product tiers** in `product_manifest.py` (CORE, EXTENDED, ADVOCATE, ADMIN, RESEARCH, DEV)
- **Module SDK** active (`app/core/module_sdk.py`) with `ModuleManifest`, `ModuleRegistry`, `register_module`

## Target State

Every feature becomes a **self-contained SDK module** with:
```
app/modules/<module_name>/
├── __init__.py          # Public API exports
├── manifest.py          # ModuleManifest declaration
├── router.py            # FastAPI router (moved from app/routers/)
├── service.py           # Business logic (moved from app/services/)
├── models.py            # Pydantic / dataclass models
├── contracts.py         # FunctionGroupContract declarations (optional)
└── README.md            # Module docs
```

## Module Boundary Map

### CORE Tier — Always Active (14 modules)

| Module | Router(s) | Services | Capabilities |
|--------|-----------|----------|--------------|
| **health** | `health` | — | ROUTER |
| **system** | `versioning` | — | ROUTER |
| **identity** | `storage`, `preamble`, `risc`, `role_ui` | `user_service` | ROUTER, CONTRACT |
| **documents** | `documents`, `vault`, `vault_engine` | `document_intake`, `document_recognition`, `document_pipeline` | ROUTER, CONTRACT, DOCUMENT |
| **timeline** | `timeline_unified` | — | ROUTER |
| **briefcase** | `briefcase` | — | ROUTER |
| **workflow** | `workflow`, `workflow_validator` | — | ROUTER, MESH |
| **rights** | `state_laws`, `law_library` | `law_engine` | ROUTER, CONTRACT |
| **tools** | `contacts`, `public_forms`, `search`, `pdf_tools`, `preview`, `document_converter` | — | ROUTER |
| **legal_analysis** | `legal_analysis` | `legal_analysis_engine` | ROUTER, CONTRACT |
| **realtime** | `websocket` | — | ROUTER |
| **free_api** | `free_api` | — | ROUTER |
| **plugins** | `plugins` | — | ROUTER, MESH |
| **components** | `components`, `core_system`, `security` | — | ROUTER |
| **mndes** | `mndes` | `mndes_api_client`, `mndes_exhibit_service` | ROUTER, CONTRACT |

### EXTENDED Tier — Legal Tools (10 modules)

| Module | Router(s) | Services | Capabilities |
|--------|-----------|----------|--------------|
| **eviction_defense** | `eviction_defense` | `eviction/*` | ROUTER, CONTRACT |
| **zoom_court** | `zoom_court`, `zoom_court_prep` | — | ROUTER |
| **court_forms** | `court_forms`, `court_packet`, `legal_filing` | `court_form_generator`, `legal_filing_service` | ROUTER, CONTRACT |
| **legal_trails** | `legal_trails` | — | ROUTER |
| **tenant_defense** | `tenant_defense` | — | ROUTER, CONTRACT |
| **case_builder** | `intake`, `guided_intake`, `case_builder`, `progress`, `actions`, `plan_maker`, `tools_api` | `case_auto_creation`, `document_flow_orchestrator` | ROUTER, CONTRACT, MESH |
| **complaints** | `complaints` | `complaint_wizard` | ROUTER, CONTRACT |
| **housing_accountability** | `housing_accountability` | — | ROUTER |
| **role_upgrade** | `role_upgrade` | — | ROUTER |

### ADVOCATE Tier — Collaboration (2 modules)

| Module | Router(s) | Services | Capabilities |
|--------|-----------|----------|--------------|
| **document_delivery** | `document_delivery`, `communication` | `document_delivery_service`, `communication_service`, `email_service` | ROUTER, CONTRACT |
| **invite_codes** | `invite_codes` | — | ROUTER |

### ADMIN Tier — Dashboards (3 modules)

| Module | Router(s) | Services | Capabilities |
|--------|-----------|----------|--------------|
| **analytics** | `analytics`, `dashboard`, `enterprise_dashboard` | — | ROUTER, WIDGET |
| **batch_ops** | `batch`, `registry` | `document_distributor` | ROUTER |
| **tenancy_hub** | `tenancy_hub` | — | ROUTER |

### RESEARCH Tier — AI Intelligence (8 modules)

| Module | Router(s) | Services | Capabilities |
|--------|-----------|----------|--------------|
| **document_ai** | `recognition`, `extraction`, `crawler`, `overlays`, `unified_overlays` | `document_intelligence`, `event_extractor`, `crawler` | ROUTER, DOCUMENT, AI |
| **research** | `research`, `form_data` | — | ROUTER, AI |
| **vault_advanced** | `vault_all_in_one`, `cloud_sync` | `vault_engine`, `vault_ingestion`, `vault_search`, `vault_upload_service` | ROUTER, DOCUMENT |
| **positronic_brain** | `brain`, `auto_mode` | `brain_integrations`, `auto_mode_orchestrator`, `auto_mode_summary_service` | ROUTER, MESH, AI, BACKGROUND |
| **emotion_engine** | `emotion` | `emotion_engine` | ROUTER, AI |
| **mesh_network** | `positronic_mesh`, `mesh_network`, `module_hub` | `mesh_handlers`, `module_actions`, `module_registration` | ROUTER, MESH |
| **functionx** | `functionx` | `functionx_service` | ROUTER |
| **funding_location** | `funding_search`, `hud_funding`, `location` | `hud_funding_guide`, `location_service` | ROUTER |
| **campaign** | `campaign`, `public_exposure`, `fraud_exposure` | `fraud_exposure` | ROUTER |
| **litigation_intelligence** | `litigation_intelligence` | — | ROUTER, AI |

### DEV Tier — Internal Tools (3 modules)

| Module | Router(s) | Services | Capabilities |
|--------|-----------|----------|--------------|
| **setup** | `setup`, `page_index`, `page_editor` | — | ROUTER, WIDGET |
| **development** | `development` | — | ROUTER |
| **data_tools** | `export_import`, `testing`, `documentation` | — | ROUTER |

## Conversion Steps (Per Module)

For each module, perform these steps:

1. **Create `app/modules/<module>/manifest.py`**
   ```python
   from app.sdk import ModuleManifest, ModuleCapability, ProductTier
   
   MANIFEST = ModuleManifest(
       name="documents",
       display_name="Document System",
       description="Upload, certify, organize tenant documents",
       version="1.0.0",
       tier=ProductTier.CORE,
       capabilities=(ModuleCapability.ROUTER, ModuleCapability.CONTRACT, ModuleCapability.DOCUMENT),
       router_module="app.modules.documents.router",
       tags=("Documents",),
   )
   ```

2. **Move router from `app/routers/<name>.py` → `app/modules/<module>/router.py`**
   - Update internal imports (e.g., `from app.services.document_intake` → `from .service`)
   - Keep route handlers identical at first — refactor later

3. **Move services from `app/services/` → `app/modules/<module>/service.py`**
   - Only move services that belong to ONE module
   - Shared services stay in `app/services/shared/` or become their own module

4. **Create `app/modules/<module>/__init__.py`**
   ```python
   from .manifest import MANIFEST
   from .router import router
   from .service import DocumentService
   
   __all__ = ["MANIFEST", "router", "DocumentService"]
   ```

5. **Update `product_manifest.py`**
   - Change `_register("app.routers.documents", ...)` to `_register("app.modules.documents.router", ...)`

6. **Delete old files** from `app/routers/` and `app/services/` once confirmed working

## Shared Services (Do NOT Module-ize)

These are used by multiple modules and stay in `app/services/shared/`:

| Service | Used By |
|---------|---------|
| `azure_ai.py` | document_ai, positronic_brain |
| `gemini_ai.py` | document_ai, positronic_brain |
| `groq_ai.py` | document_ai, positronic_brain |
| `cloud_providers.py` | documents, vault_advanced |
| `token_manager.py` | identity, documents, vault_advanced |
| `auth_service.py` | identity, document_delivery |

## Migration Order (Risk-Minimized)

Phase 1 (Low Risk, Learn Pattern):
1. `health` — simplest router, no services
2. `free_api` — simple, no dependencies
3. `contacts` — simple CRUD

Phase 2 (Medium Risk, Test Integration):
4. `documents` — complex, but well-understood
5. `timeline` — medium complexity
6. `eviction_defense` — important feature

Phase 3 (High Risk, Core Features):
7. `identity` / `storage` — gate system, affects all users
8. `case_builder` — many sub-routers
9. `positronic_brain` — mesh integration

Phase 4 (Remaining):
10. All remaining modules in tier order (DEV → RESEARCH → ADMIN → ADVOCATE → EXTENDED)

## Verification Checklist

After each module conversion:
- [ ] `python -m py_compile app/modules/<module>/*.py`
- [ ] App imports successfully: `from app.main import app`
- [ ] Module manifest valid: `ModuleRegistry().validate()["valid"] is True`
- [ ] Routes accessible: `curl http://localhost:8000/docs` shows module tags
- [ ] No old `app/routers/<name>.py` file exists (or has deprecation warning)
