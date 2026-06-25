# Semptify Status Audit — 2026-06-21

> Snapshot of module/function/contract engagement across the codebase.
> Classification: **WORKING** / **PARTIAL** / **STUB** / **CONCEPT** / **HOLE**

---

## 1. Headline Counts

| Metric | Count |
|---|---|
| Active module registrations in `product_manifest.py` | **95** |
| INACTIVE modules (commented out) | **6** |
| Total Python modules under `app/modules/` | ~75 directories/files |
| `FunctionGroupContract` registrations | **~49** across 12 modules |
| Modules WITH contracts | **12** |
| Modules WITHOUT contracts (registered but no contract) | **~70+** |
| `NotImplementedError` sites | **6** |
| `"not_implemented"` status returns | **11** (all in `free_api_pack.py`) |
| `TODO` / `FIXME` / `XXX` / `HACK` markers | **53** across 26 files |
| `pass`-only function bodies in modules | **60** across 33 files |
| HTML pages with "Coming soon/placeholder/stub/TODO" | **148** across 36 files |

---

## 2. Module Registrations by Tier

### CORE TIER — 32 registrations
| Module | Lifecycle | Notes |
|---|---|---|
| `health.router` | stable | |
| `core.versioning` | stable | |
| `preamble.router` | stable | |
| `risc.router` | stable | |
| `role_ui.router` | stable | SSOT-compliant |
| `storage.router` | stable | |
| `user.router` | stable | 2 contracts (act_as_start/stop) |
| `rent.router` | stable | 5 contracts |
| `auth.router` | stable | |
| `onboarding.reconnect` | stable | |
| `documents.router` | stable | |
| `vault.router` | stable | 6 contracts (upload/folders/init/search/ingestion) |
| `vault_engine.router` | stable | |
| `timeline.router` | stable | 1 contract (chronology) |
| `briefcase.router` | stable | |
| `workflow.router` | stable | |
| `workflow_validator.router` | stable | |
| `state_laws.router` | **beta** | Only MN complete. Need NY/CA/TX/FL/IL |
| `law_library.router` | stable | 2 registrations (api + page) |
| `contacts.router` | stable | |
| `public_forms.router` | stable | |
| `search.router` | stable | |
| `pdf_tools.router` | stable | |
| `preview.router` | stable | |
| `document_converter.router` | stable | |
| `legal_analysis.router` | stable | |
| `websocket.router` | stable | |
| `free_api.router` | stable | **STUB — all 11 endpoints return `not_implemented`** |
| `core_system.router` | stable | |
| `security.router` | stable | 2FA stubs fallback if advanced_security missing |
| `mndes.router` | **beta** | **3 NotImplementedError — REST client awaits MN Supreme Court API** |

### EXTENDED TIER — 19 registrations
| Module | Lifecycle | Notes |
|---|---|---|
| `fems.router` | stable | |
| `eviction_defense.router` | stable | |
| `zoom_court.router` | stable | |
| `zoom_court_prep.router` | stable | |
| `court_forms.router` | stable | 2 contracts (form_generate, form_autofill) |
| `court_packet.router` | stable | |
| `legal_trails.router` | stable | |
| `tenant_defense` | stable | |
| `intake.router` | stable | |
| `guided_intake.router` | stable | |
| `case_builder.router` | stable | |
| `progress.router` | stable | |
| `actions.router` | stable | |
| `plan_maker.router` | stable | |
| `tools_api.router` | stable | |
| `complaints.router` | stable | |
| `housing_accountability.router` | **beta** | **`detect_repeated_fees()` is a stub** |
| `housing_accountability.pattern_history` | **beta** | Depends on housing_accountability |
| `role_upgrade.router` | stable | |

### ADVOCATE TIER — 3 registrations
| Module | Lifecycle | Notes |
|---|---|---|
| `document_delivery.router` | stable | 4 contracts (send/inbox/sign/reject) |
| `communication.router` | stable | 4 contracts (conversation/message/list/fill_sign) |
| `invite_codes.router` | stable | |

### ADMIN TIER — 9 registrations
| Module | Lifecycle | Notes |
|---|---|---|
| `admin_console.router` | stable | 5 contracts (user_list/detail/impersonate x2/system_status) |
| `admin_console.module_flags` | **internal** | 4 contracts (list/set/delete/preview) |
| `analytics.router` | stable | |
| `dashboard.router` | stable | |
| `enterprise_dashboard.router` | stable | |
| `batch.router` | stable | |
| `registry.router` | stable | |
| `tenancy_hub.router` | stable | |
| `capabilities.router` | stable | |

### RESEARCH TIER — 20 registrations
| Module | Lifecycle | Notes |
|---|---|---|
| `recognition.router` | stable | |
| `extraction.router` | stable | |
| `crawler.router` | stable | |
| `research.router` | stable | |
| `form_data.router` | stable | |
| `unified_overlays.router` | stable | 5 contracts (overlay CRUD + compose_view) |
| `vault_all_in_one.router` | stable | |
| `cloud_sync.router` | stable | |
| `brain.router` | **experimental** | Heavy service, feature-flagged |
| `emotion.router` | **experimental** | |
| `positronic_mesh.router` | **experimental** | Heavy service |
| `mesh_network.router` | **experimental** | feature_flag=beta_mesh_network |
| `module_hub.router` | **experimental** | Heavy service |
| `functionx.router` | **dev_only** | **CONCEPT — "FunctionX concept not yet defined"** |
| `funding_search.router` | stable | |
| `hud_funding.router` | stable | |
| `location.router` | stable | |
| `campaign.router` | stable | |
| `public_exposure.router` | stable | |
| `fraud_exposure.router` | stable | |

### DEV TIER — 12 registrations
| Module | Lifecycle | Notes |
|---|---|---|
| `setup.router` | stable | |
| `page_index.router` | stable | |
| `page_editor.router` | stable | |
| `development.router` | stable | |
| `dev_lab.router` | **dev_only** | 4 contracts (list/status/promote/test) |
| `dev_lab.ideas` | **dev_only** | 3 contracts (list/submit/promote) |
| `filedored.router` | stable | 2 contracts (document_process, folders_ensure) |
| `data_freshness.router` | stable | |
| `inventory.router` | stable | |
| `export_import.router` | stable | |
| `testing.router` | stable | |
| `documentation.router` | stable | |

### INACTIVE (commented out in manifest) — 6
| Module | Reason |
|---|---|
| `plugins.router` | Marketplace not built |
| `components.router` | Dev scaffolding |
| `legal_filing.router` | Not integrated with mesh/network |
| `auto_mode.router` | Not production-ready |
| `litigation_intelligence.router` | graph_engine not implemented, dataclass errors |
| `graph_engine` (inside LIS) | TODO — not implemented |

---

## 3. Contract Coverage

### Modules WITH `FunctionGroupContract` registrations (12)
| Module | Contracts | Count |
|---|---|---|
| `vault` | vault_upload, vault_folders, vault_init, vault_search, vault_ingestion | 6 |
| `overlays` | overlay_create, overlay_query, overlay_update, overlay_delete, overlay_compose_view | 5 |
| `admin_console` | user_list, user_detail, impersonate_start, impersonate_stop, system_status | 5 |
| `rent` | payment_create, payment_list, +3 more | 5 |
| `delivery` | document_send, inbox_list, document_sign, document_reject | 4 |
| `communication` | conversation_create, message_send, conversations_list, document_fill_sign | 4 |
| `admin_console.module_flags` | module_flags_list, module_flags_set, module_flags_delete, module_flags_preview | 4 |
| `dev_lab` | dev_modules_list, dev_module_status, dev_module_promote, dev_module_test | 4 |
| `court_forms` | form_generate, form_autofill | 2 |
| `filedored` | document_process, folders_ensure | 2 |
| `duplicates` | detect, list_all | 2 |
| `user` | act_as_start, act_as_stop | 2 |
| `dev_lab.ideas` | ideas_list, ideas_submit, ideas_promote | 3 |
| `timeline` | timeline_chronology | 1 |

### Modules WITHOUT contracts (~70+ registered)
Every other registered module has **zero** `FunctionGroupContract` registrations. This is the largest "hole" in the system — most modules expose no SSOT contract, meaning callers cannot reliably integrate against them.

**High-priority modules missing contracts:**
- `documents.router` — core document management, no contract
- `storage.router` — OAuth + storage connection, no contract
- `auth.router` — authentication, no contract
- `onboarding.reconnect` — no contract
- `state_laws.router` — no contract
- `law_library.router` — no contract
- `mndes.router` — no contract (and has 3 NotImplementedError)
- `housing_accountability.router` — no contract (and has stub)
- `eviction_defense.router` — no contract
- `case_builder.router` — no contract
- `complaints.router` — no contract
- `invite_codes.router` — no contract
- `analytics.router` — no contract
- `batch.router` — no contract
- `registry.router` — no contract
- `capabilities.router` — no contract
- `unified_overlays.router` — no contract (but `overlays` service has 5)
- `vault_all_in_one.router` — no contract (but `vault` service has 6)
- `recognition.router`, `extraction.router`, `crawler.router` — no contracts
- `brain.router`, `emotion.router`, `mesh_network.router` — no contracts

---

## 4. Stub / Placeholder Inventory

### Hard stubs (NotImplementedError — will crash if called)
| File | Function | Reason |
|---|---|---|
| `app/services/mndes_api_client.py:193` | `MNDESRestClient.submit_exhibit` | Awaiting MN Supreme Court API |
| `app/services/mndes_api_client.py:202` | `MNDESRestClient.get_submission_status` | Awaiting MN Supreme Court API |
| `app/services/mndes_api_client.py:208` | `MNDESRestClient.get_case_exhibits` | Awaiting MN Supreme Court API |
| `app/core/shutdown.py` (2 sites) | — | Investigate |
| `app/core/product_manifest.py` (1 site) | — | Investigate |

### Soft stubs (returns `{"status": "not_implemented"}`)
All 11 in `app/modules/free_api_pack.py`:
- `PropertyLookup.lookup_parcel`, `PropertyLookup.lookup_address`
- `LandlordLookup.lookup_business`, `LandlordLookup.lookup_owner`
- `CourtScraper.search_evictions`, `CourtScraper.fetch_federal_cases`
- `Violations.city_inspections`, `Violations.environmental_violations`
- `Inspections.hud_reac`, `Inspections.local_inspections`
- `Statutes.get_statute`

### Known stubs (per `dev_notes` in manifest)
- `state_laws.router` — only MN complete, need NY/CA/TX/FL/IL
- `mndes.router` — 3 NotImplementedError pending external API
- `housing_accountability.router` — `detect_repeated_fees()` at router.py:83 is a stub
- `functionx.router` — "FunctionX concept — not yet defined"

### TODO markers (53 across 26 files)
Top offenders:
- `app/core/page_contracts.py` — 16 TODOs
- `app/modules/_template/service.py` — 4 TODOs (expected, it's a template)
- `app/modules/litigation_intelligence/router.py` — 4 TODOs (graph_engine)
- `app/services/document_registry.py` — 4 TODOs
- `app/modules/document_converter.py` — 2 TODOs
- `app/modules/litigation_intelligence/__init__.py` — 2 TODOs
- `app/sdk/flask_converter.py` — 2 TODOs
- 19 more files with 1 TODO each

### `pass`-only function bodies (60 across 33 files)
Top offenders:
- `app/modules/components/router.py` — 11 pass bodies (INACTIVE module, but code exists)
- `app/modules/court_forms/router.py` — 5
- `app/modules/case_builder/router.py` — 3
- `app/modules/timeline/router.py` — 3
- `app/modules/vault/router.py` — 3
- 29 more files with 1-2 pass bodies

### HTML pages with "Coming soon/placeholder/stub/TODO" (148 across 36 files)
Top offenders:
- `static/tenant/tools/letters.html` — 28
- `static/tools/generators.html` — 15
- `static/components/preview-modal.html` — 10
- `static/tools/calculators.html` — 8
- `static/library.html` — 7
- `static/office/signer.html` — 7
- `static/admin/dev_lab.html` — 6 (expected, placeholders for dynamic content)
- `static/onboarding/validation/validate-legal.html` — 6
- `static/admin/module_flags.html` — 5
- `static/admin/dashboard.html` — 4
- 26 more files with 1-4 markers

---

## 5. Classification Summary

| Class | Count | Examples |
|---|---|---|
| **WORKING** | ~50 | vault, timeline, overlays, delivery, communication, admin_console, dev_lab, rent, user, court_forms, filedored, duplicates |
| **PARTIAL** | ~15 | state_laws (MN only), mndes (3 stubs), housing_accountability (1 stub), security (2FA fallback), free_api (all stubs) |
| **STUB** | ~5 | free_api_pack (11 stubs), functionx (concept), components (11 pass bodies, INACTIVE) |
| **CONCEPT** | ~3 | functionx, plugins (marketplace), legal_filing (mesh integration) |
| **HOLE** | ~70+ | Most registered modules have zero contracts; many HTML pages have "coming soon" sections |

---

## 6. Holes to Fill (Priority Order)

### Tier 1 — Contracts for core modules
- [ ] `documents.router` — needs contract
- [ ] `storage.router` — needs contract
- [ ] `auth.router` — needs contract
- [ ] `state_laws.router` — needs contract + NY/CA/TX/FL/IL data
- [ ] `mndes.router` — needs contract + REST client implementation (blocked on external API)
- [ ] `housing_accountability.router` — needs contract + `detect_repeated_fees()` implementation
- [ ] `eviction_defense.router` — needs contract
- [ ] `case_builder.router` — needs contract
- [ ] `complaints.router` — needs contract
- [ ] `invite_codes.router` — needs contract

### Tier 2 — Implement stubs
- [ ] `free_api_pack.py` — implement all 11 API methods (real HTTP calls to free APIs)
- [ ] `housing_accountability.detect_repeated_fees()` — implement pattern detection
- [ ] `state_laws` — add NY, CA, TX, FL, IL statute data
- [ ] `mndes_api_client.py` — implement REST client when MN Supreme Court API is available
- [ ] `litigation_intelligence.graph_engine` — implement or remove module

### Tier 3 — HTML page content (148 markers)
- [ ] `static/tenant/tools/letters.html` — 28 placeholders
- [ ] `static/tools/generators.html` — 15 placeholders
- [ ] `static/components/preview-modal.html` — 10 placeholders
- [ ] `static/tools/calculators.html` — 8 placeholders
- [ ] `static/library.html` — 7 placeholders
- [ ] `static/office/signer.html` — 7 placeholders
- [ ] 30 more HTML files with placeholders

### Tier 4 — TODOs in code
- [ ] `app/core/page_contracts.py` — 16 TODOs
- [ ] `app/services/document_registry.py` — 4 TODOs
- [ ] `app/modules/document_converter.py` — 2 TODOs
- [ ] 23 more files with TODOs

---

## 7. Next Steps (Parked for Future Sessions)

1. **Contract backfill** — write `FunctionGroupContract` registrations for the 10 Tier-1 modules above. This is the highest-leverage work because contracts enable deterministic integration.
2. **Stub implementation** — implement `free_api_pack.py` (11 stubs) and `housing_accountability.detect_repeated_fees()`. These are real user-facing features currently returning nothing.
3. **HTML placeholder sweep** — 148 placeholders across 36 HTML files. Many are "coming soon" sections that need real content. This ties into the **Context Engine** todo (feed every page with verified facts).
4. **TODO sweep** — 53 TODOs across 26 files. Triage into "real TODO" vs "aspirational comment" vs "dead code".
5. **INACTIVE modules** — decide whether to delete `plugins`, `components`, `legal_filing`, `auto_mode`, `litigation_intelligence` or revive them.

---

*Generated 2026-06-21 by audit task. Snapshot, not a live document.*
