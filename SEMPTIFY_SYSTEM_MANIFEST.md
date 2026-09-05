# SEMPTIFY SYSTEM MANIFEST

**Version:** 5.0.0 | **Last Updated:** 2026-09-05

> **How to read this file:** Parts 1–4 contain stable project identity and rules that
> change rarely. Part 5 is a **dated snapshot** generated from the live code — it is
> accurate as of the date on it, but `app/core/product_manifest.py` is always the live
> source of truth. Run `MANIFEST.summary()` (see Part 5 header) to verify before
> trusting any count or table here. The canonical current work state is
> `ACTIVE_CONTEXT.md`; the canonical build log is `BUILD_STATE.md`.
>
> - Active worktree: `C:\master-repo\modules\app-semptify-fastapi\`
> - Canonical source mirror: `C:\master-repo\sources\app-semptify-fastapi\`

This is the FIRST file any AI or developer must read before touching Semptify. It defines what is active, the rules for adding modules, and where the live truth lives.

---

## PART 1 — PROJECT IDENTITY

| Item | Value |
| --- | --- |
| App Name | Semptify |
| Version | 5.0.0 |
| Mission | Tenant rights protection — a public utility, not a product (nonprofit, pre-filing) |
| Root Path | `C:\master-repo\modules\app-semptify-fastapi\` |
| Entry Point | `app/main.py` (DO NOT add routers here directly) |
| Manifest | `app/core/product_manifest.py` (SINGLE SOURCE OF TRUTH) |
| Python | **3.11.9 ONLY — hard enforced, kills server if wrong** |
| Venv | `venv311\Scripts\Activate.ps1` |
| Database (dev) | SQLite — `semptify.db` |
| Database (prod) | PostgreSQL via `DATABASE_URL` in `.env` (pgvector for embeddings) |
| DB ORM | SQLAlchemy async (`app.core.database`) |
| DB Base Class | `app.core.database.Base` — ALL models must use this |
| Config | `app.core.config.get_settings()` |
| Auth | Cookie-based via `app.core.cookie_auth.extract_user_id`; signed `semptify_uid` cookie |
| Templates | Jinja2 at `app/templates/` |
| Static Files | `static/` |
| Uploads | `uploads/vault/` |
| Document storage | **User's own cloud** (Google Drive / Dropbox / OneDrive via OAuth) — Semptify holds no tenant documents |
| Hosting | Render (Docker runtime, `python:3.11-slim`), public at `semptify.org` via Cloudflare tunnel |

---

## PART 2 — THE GOLDEN RULE

### Never add `app.include_router()` directly to `main.py`

All modules are declared in `app/core/product_manifest.py` and loaded via:

```python
register_tiers(fastapi_app, *enabled_tiers)
```

To add a new module — only 3 steps:

1. Create files in `app/modules/your_module/`
2. Add one `_register(...)` line to `product_manifest.py`
3. If needed, ensure the tier is enabled for the target environment

**Do not touch anything else.** See `MODULE_BLUEPRINT.md` (Part 0A) for the required
blueprint that must exist and be approved *before* any module is built.

---

## PART 3 — PRODUCT TIERS (corrected 2026-09-05)

| Tier | Purpose | Production | Development |
| --- | --- | --- | --- |
| `CORE` | Tenant-rights essentials | ✅ on | ✅ on |
| `EXTENDED` | Legal tools: eviction defense, court forms, case builder | ✅ on | ✅ on |
| `ADVOCATE` | Advocate network: delivery, collaboration, invite codes | ✅ on | ✅ on |
| `ADMIN` | Dashboards, analytics, batch ops, registry | ✅ on | ✅ on |
| `RESEARCH` | AI intelligence: recognition, extraction, crawlers | ❌ off | ✅ on |
| `DEV` | Internal dev tools | ❌ off | ✅ on |

Enabled tiers come from `_LIVE_TIERS` in `app/main.py`, keyed by `SEMPTIFY_ENV`
(default `production`). A minimal allow-listed build exists for the Render free tier
via `DEPLOY_TARGET=render_mvp` (`get_mvp_allowed_modules()` in `product_manifest.py`).

> **Correction note:** the previous version of this file said only CORE + DEV were
> active and that EXTENDED was disabled. That was stale — production has run
> CORE + EXTENDED + ADVOCATE + ADMIN since `_LIVE_TIERS` was introduced.

---

## PART 4 — MODULE DEVELOPER RULES (For Any AI or Human)

1. **Read `AGENTS.md` first** — preflight order: `AGENTS.md` → `ACTIVE_CONTEXT.md` → `BUILD_STATE.md` → `PROJECT_BIBLE.md`.
2. **`product_manifest.py` is the only place** to register routers.
3. **Blueprint before code** — no module is built without an approved blueprint in `docs/blueprints/` (see `MODULE_BLUEPRINT.md` Part 0A).
4. **Every module belongs to exactly one pillar**: RECORD / KNOW / ACT / GOVERN (see `.devin/rules/06-four-pillars.md`).
5. **Contracts are SSOT** — capabilities are declared as `FunctionGroupContract`s; if a method/field isn't in the contract, it doesn't exist. Never invent API signatures.
6. **Never use `psycopg2`** — SQLAlchemy async only. Never create a new `Base`.
7. **Never hardcode config** — use `get_settings()` or `.env`.
8. **`optional=True` on all new modules** — Semptify must start even if the module fails.
9. **Python 3.11.9 only.**
10. **Health endpoint required** — every module needs a `/health` route.
11. **No circular imports** — modules must not import from each other.
12. **PII boundary** — PII lives in overlays in the user's vault (`UnifiedOverlayManager`), not in PostgreSQL. PostgreSQL holds structure and pointers only.
13. **SSOT redirects** — `navigation.get_stage(...)`, never hardcoded URL strings.
14. **Async only** — no synchronous HTTP clients inside `async` code paths (token refresh, storage I/O).
15. **`utc_now()` from `app.core.utc`** — never bare `datetime.now()`.
16. **`app/modules/onboarding/` is NO-TOUCH** — standing rule; ask Brad first, every time.

---

## PART 5 — CURRENT MANIFEST SNAPSHOT (generated 2026-09-05)

Generated by `MANIFEST.summary()` and `MANIFEST.all()` under `venv311`. To refresh:

```powershell
.\venv311\Scripts\python.exe -c "from app.core.product_manifest import MANIFEST; import json; print(json.dumps(MANIFEST.summary(), indent=1))"
```

**Totals:** 123 registered entries — core 45, extended 21, advocate 4, admin 16, research 17, dev 20.
**Lifecycle:** 100 stable, 12 beta, 7 dev_only, 2 experimental, 1 internal, 1 deprecated.
**Validation:** no duplicate module_path+router_attr pairs.

Module paths below are shortened (`app.modules.` prefix dropped; `app.core.` shown as `core:`).

### CORE (45)

| Module | Prefix | Lifecycle |
| --- | --- | --- |
| `health.router` | `-` | stable |
| `core:versioning` | `-` | stable |
| `preamble.router` | `-` | stable |
| `risc.router` | `-` | stable |
| `role_ui.router` | `-` | stable |
| `storage.router` | `-` | stable |
| `user.router` | `-` | stable |
| `rent.router` | `/api/rent` | stable |
| `auth.router` | `-` | stable |
| `onboarding.reconnect` | `-` | stable |
| `documents.router` | `-` | stable |
| `vault.router` | `/api/vault` | stable |
| `vault_engine.router` | `/api/vault-engine` | dev_only |
| `timeline.router` | `/api/timeline` | stable |
| `eviction_timeline.router` | `/api/eviction-timeline` | stable |
| `briefcase.router` | `-` | stable |
| `packet_builder.router` | `-` | stable |
| `workflow.router` | `-` | stable |
| `workflow_validator.router` | `-` | stable |
| `state_laws.router` | `-` | beta |
| `law_library.router` | `-` | stable |
| `law_library.router` | `-` | stable |
| `contacts.router` | `-` | stable |
| `journal.router` | `/api/journal` | beta |
| `public_forms.router` | `-` | stable |
| `voice.router` | `/api/voice` | beta |
| `resource_directory.router` | `-` | beta |
| `search.router` | `/api/search` | stable |
| `pdf_tools.router` | `-` | stable |
| `preview.router` | `/api/preview` | stable |
| `document_converter.router` | `-` | stable |
| `legal_analysis.router` | `-` | stable |
| `context_engine.router` | `-` | stable |
| `page_composer.router` | `-` | stable |
| `portal.router` | `-` | stable |
| `portal.router` | `-` | stable |
| `ui_composer.router` | `-` | stable |
| `tenant_feed.router` | `-` | stable |
| `websocket.router` | `/ws` | stable |
| `free_api.router` | `-` | stable |
| `core_system.router` | `-` | stable |
| `security.router` | `/api/security` | stable |
| `mndes.router` | `-` | beta |
| `data_freshness.router` | `-` | stable |
| `page_shell.router` | `/api/page-shell` | stable |

### EXTENDED (21)

| Module | Prefix | Lifecycle |
| --- | --- | --- |
| `fems.router` | `-` | stable |
| `eviction_defense.router` | `-` | stable |
| `zoom_court.router` | `-` | stable |
| `zoom_court_prep.router` | `-` | stable |
| `court_forms.router` | `-` | stable |
| `court_packet.router` | `-` | stable |
| `legal_trails.router` | `-` | stable |
| `legal.router` | `-` | stable |
| `intake.router` | `-` | stable |
| `guided_intake.router` | `-` | stable |
| `case_builder.router` | `-` | stable |
| `progress.router` | `-` | stable |
| `actions.router` | `-` | stable |
| `plan_maker.router` | `-` | stable |
| `tools_api.router` | `-` | stable |
| `complaints.router` | `-` | stable |
| `housing_accountability.router` | `-` | beta |
| `housing_accountability.pattern_history` | `-` | beta |
| `external_mappings.router` | `-` | beta |
| `dispute_tracker.router` | `/api/dispute-tracker` | beta |
| `role_upgrade.router` | `-` | stable |

### ADVOCATE (4)

| Module | Prefix | Lifecycle |
| --- | --- | --- |
| `document_delivery.router` | `-` | stable |
| `communication.router` | `-` | stable |
| `invite_codes.router` | `-` | stable |
| `advocate.router` | `-` | stable |

### ADMIN (16)

| Module | Prefix | Lifecycle |
| --- | --- | --- |
| `system_health.router` | `/api/admin/system` | stable |
| `run_modules.router` | `/api/admin/run` | stable |
| `correspondence.router` | `/api/admin/correspondence` | stable |
| `user_concerns.router` | `/api/admin/user-concerns` | stable |
| `advanced.router` | `/api/admin/advanced` | stable |
| `admin_console.router` | `/admin-console` | stable |
| `admin_console.module_flags` | `-` | internal |
| `analytics.router` | `/api/analytics` | stable |
| `dashboard.router` | `-` | stable |
| `enterprise_dashboard.router` | `-` | stable |
| `batch.router` | `/api/batch` | stable |
| `registry.router` | `-` | stable |
| `tenancy_hub.router` | `-` | stable |
| `capabilities.router` | `-` | stable |
| `manager.router` | `-` | stable |
| `funding_mgmt.router` | `-` | beta |

### RESEARCH (17 — development only)

| Module | Prefix | Lifecycle |
| --- | --- | --- |
| `recognition.router` | `-` | stable |
| `extraction.router` | `-` | stable |
| `crawler.router` | `-` | stable |
| `research.router` | `-` | stable |
| `form_data.router` | `/api/form-data` | stable |
| `unified_overlays.router` | `-` | stable |
| `cloud_sync.router` | `-` | stable |
| `emotion.router` | `-` | experimental |
| `module_hub.router` | `/api` | experimental |
| `functionx.router` | `-` | dev_only |
| `funding_search.router` | `-` | stable |
| `hud_funding.router` | `-` | stable |
| `location.router` | `-` | stable |
| `campaign.router` | `-` | stable |
| `public_exposure.router` | `-` | stable |
| `fraud_exposure.router` | `-` | stable |
| `litigation_intelligence.router` | `-` | stable |

### DEV (20 — development only)

| Module | Prefix | Lifecycle |
| --- | --- | --- |
| `setup.router` | `/api/setup` | stable |
| `page_index.router` | `-` | stable |
| `page_editor.router` | `-` | stable |
| `development.router` | `-` | stable |
| `dev_lab.router` | `/dev/lab` | dev_only |
| `agent_orchestrator.router` | `/api/agent-orchestrator` | dev_only |
| `dev_lab.ideas` | `/dev/lab/ideas` | dev_only |
| `filedored.router` | `-` | stable |
| `inventory.router` | `-` | stable |
| `judge.router` | `-` | deprecated |
| `calendar.router` | `/api/calendar` | beta |
| `tactics.router` | `-` | beta |
| `example_payment_tracking` | `-` | dev_only |
| `legal_filing_module` | `-` | dev_only |
| `context_loop.router` | `-` | stable |
| `vault_installer.routes` | `-` | stable |
| `export_import.router` | `/api/export-import` | stable |
| `testing.router` | `/api/testing` | stable |
| `documentation.router` | `/api/docs` | stable |
| `document_center.router` | `/api/dc` | stable |

> Snapshot notes: `law_library.router` and `portal.router` each appear twice with
> different router attributes (not duplicates per `MANIFEST.validate()`).

---

## PART 6 — START / STOP COMMANDS

```powershell
# Activate environment
cd "C:\master-repo\modules\app-semptify-fastapi"
.\venv311\Scripts\Activate.ps1

# Start server (dev)
python -m uvicorn app.main:fastapi_app --host 127.0.0.1 --port 8001 --reload

# Verify health
Invoke-RestMethod http://127.0.0.1:8001/health
```

---

*For what is being worked on right now: `ACTIVE_CONTEXT.md`. For what shipped and what is broken: `BUILD_STATE.md`. For governance: `PROJECT_BIBLE.md`. For the Known Failure Registry: `AGENTS.md`.*
