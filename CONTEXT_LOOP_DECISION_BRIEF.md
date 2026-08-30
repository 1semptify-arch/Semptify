# CONTEXT_LOOP_DECISION_BRIEF.md

## 1. Summary of the fork

The `context_loop` logic exists as two independent implementations in `main`:

- `app/modules/context_loop/service.py` — the "module" copy, promoted to a FastAPI router under `/api/core/*` and wired to the event bus at startup via `subscribe_context_loop_events()` in `app/main.py`.
- `app/services/context_loop.py` — the "service" copy, used as a state store and event emitter by other services (`document_pipeline`, `case_auto_creation`, `adaptive_ui`, `page_composer`, `module_hub`, `ui_composer`).

Both files trace back to the initial commit (`eb8e401d Initial commit: Semptify-FastAPI v5.0.0`) and the early `app/services` re-export stub commit (`72d82574 Add app/services re-export stubs for modular imports`). Over time the module copy grew an HTTP router and product-manifest registration, while the service copy gained optional `data_freshness_manager` integration that the module copy does not have. The `adr-0008-pilot` branch carries both files as well, with only cosmetic differences from `main` (StrEnum -> `(str, Enum)`, emoji -> ASCII glyphs, import ordering). `tools/gap_report.py` already documents this as an architectural gap requiring an owner decision.

## 2. Side-by-side: the two `context_loop` implementations

| | **A: `app/modules/context_loop/service.py`** | **B: `app/services/context_loop.py`** |
|---|---|---|
| **Lines (main)** | 1152 | 1147 |
| **Path type** | Module (`app/modules/context_loop/`) | Service (`app/services/`) |
| **Primary role** | Event-bus subscriber + HTTP API router backing | In-memory state store + event emitter for other services |
| **Top-level classes** | `ContextDataLoop`, `IntensityEngine`, `ContextEvent`, `UserContext`, `EventType`, `Severity` | `ContextDataLoop`, `IntensityEngine`, `ContextEvent`, `UserContext`, `EventType`, `Severity` |
| **Public methods** | `emit_event()`, `get_state()`, `get_intensity_report()`, `get_context()`, `register_processor()`, `register_listener()`, `_get_recommended_actions()` (public-by-underscore) | `emit_event()`, `get_state()`, `get_intensity_report()`, `get_context()`, `register_processor()`, `register_listener()`, `_get_recommended_actions()` (public-by-underscore) |
| **Module-only surface** | `subscribe_context_loop_events()` (module-level); event-bus wire-up `_on_document_added`, `_on_document_processed`, `_on_document_classified`, `_on_events_extracted`, `_on_case_updated`, `_on_timeline_updated`, `_on_deadline_added`, `_on_deadline_approaching`, `_on_violation_found` | n/a |
| **Service-only surface** | n/a | `ContextEvent.validate_freshness()`, `UserContext.calculate_freshness_score()`, `UserContext.validate_context_freshness()` (all guarded by an optional `data_freshness_manager` import) |
| **Global instances** | `context_loop = ContextDataLoop()`; `intensity_engine = context_loop.intensity_engine` | `context_loop = ContextDataLoop()`; `intensity_engine = context_loop.intensity_engine` |
| **State owned** | In-memory only: `self.contexts: dict[str, UserContext]`, `self.event_queue`, `self.processors`, `self.listeners`; `IntensityEngine.intensity_history` | In-memory only: same fields; also calls out to optional `data_freshness_manager` at runtime |
| **DB tables** | None | None |
| **Persistent files/caches** | None | None (freshness is a runtime lookup, not a persisted cache) |
| **Callers / importers** | `app/main.py` (wires subscribers at startup); `app/modules/context_loop/router.py` (HTTP routes under `/api/core/*`); `app/core/product_manifest.py` (registers `app.modules.context_loop.router`); `tools/_seed_orchestrator_tasks.json` references this file as the canonical `context_loop` path | `app/services/document_pipeline.py` (imports `EventType, context_loop`, calls `emit_event` on upload/analysis/action); `app/services/case_auto_creation.py` (imports `EventType, context_loop`, calls `emit_event`); `app/services/adaptive_ui.py` (imports `context_loop`, calls `get_context` and `get_intensity_report`); `app/modules/page_composer/assembly.py` (imports `context_loop`, calls `get_state`); `app/core/module_hub.py` (imports `context_loop`, calls `get_state`); `app/services/ui_composer.py` (imports `context_loop`, calls `get_user_context` which does not exist); `tests/test_page_composer_assembly.py` and `tests/test_page_composer_assembly_api.py` patch `app.services.context_loop.context_loop.get_state` |
| **Tests exercising it** | `tests/module_health/test_context_loop.py` (auto-generated health check) | No direct unit tests; used indirectly via the B callers, which currently pass because they import the separate `app/services/context_loop.py` instance |
| **Test pass status (this run)** | `pytest tests/module_health/test_context_loop.py` passed | `pytest tests/test_copilot.py` (state/intensity/predictions/health/deadline/issue endpoints) passed; no dedicated test file found |
| **Last 5 `git log --follow` commits (main)** | `5ee8b4e3`, `163820f9`, `4d01e4a2`, `99084e3f`, `a27f9789` | `5ee8b4e3`, `163820f9`, `99084e3f`, `b19b5df3`, `370118a0` |
| **Pilot diff vs main** | Cosmetic only: `StrEnum` -> `(str, Enum)`, emoji -> ASCII glyphs, import order. Functional code is identical. | Cosmetic only: same style changes. Functional code is identical. |
| **Notable issues** | `_on_deadline_approaching` and `_on_violation_found` call `await context_loop.process_input(...)`, but `process_input` is not defined anywhere in the repository. | `app/services/ui_composer.py` calls `context_loop.get_user_context(user_id)`, but `get_user_context` is not defined anywhere in the repository. |

## 3. Side-by-side: `app/core/features.py` vs `app/core/feature_flags.py`

| | **`app/core/features.py`** | **`app/core/feature_flags.py`** |
|---|---|---|
| **Lines (main)** | 421 | 87 |
| **Storage model** | PostgreSQL/SQLite `feature_flags` table, plus an in-memory 60-second cache, plus environment-variable overrides (`FEATURE_<NAME>=true/false`). | Pure in-memory class variable `_flags: dict[str, bool]`; no persistence and no cache TTL. |
| **Flag definitions** | `Feature` StrEnum with 24 flags: `AI_COPILOT`, `AI_DOCUMENT_ANALYSIS`, `AI_LEGAL_ADVICE`, `DOCUMENT_OCR`, `DOCUMENT_SIGNING`, `BULK_UPLOAD`, `COURT_FORMS`, `COMPLAINT_WIZARD`, `EVICTION_DEFENSE`, `PREMIUM_EXPORT`, `PREMIUM_TEMPLATES`, `UNLIMITED_STORAGE`, `BETA_DASHBOARD`, `BETA_TIMELINE_V2`, `BETA_MESH_NETWORK`, `REDIS_CACHE`, `DISTRIBUTED_MESH`, `WEBSOCKET_EVENTS`, `TWO_FACTOR_AUTH`, `AUDIT_LOGGING`, `RATE_LIMITING`, `EXPERIMENTAL_AI_MODEL`, `EXPERIMENTAL_UI`. | Hard-coded `_flags` with 6 flags: `admin_access`, `copilot`, `voice_to_text`, `communication_import`, `resource_directory`. |
| **API surface** | `features.is_enabled()`, `features.is_enabled_for_user()`, `features.is_enabled_for_role()`, `features.set_enabled()`, `features.get_all_flags()`, `features.get_status()`, `require_feature()` decorator, `require_feature_for_user()` decorator, `ensure_schema()`. | `FeatureFlags.is_enabled()`, `FeatureFlags.set_flag()`, `FeatureFlags.toggle_flag()`, `FeatureFlags.all_flags()`, `flag_for_path()`, `FeatureFlagMiddleware.dispatch()`. |
| **Middleware** | No middleware. | `FeatureFlagMiddleware` — blocks HTTP requests by path prefix with `503 Service Unavailable` when the guarding flag is disabled. |
| **Path-to-flag map** | n/a | `/admin` -> `admin_access`; `/api/copilot` and `/tenant/copilot` -> `copilot`; `/api/voice` -> `voice_to_text`; `/api/import` -> `communication_import`; `/api/resources` and `/tenant/resources` -> `resource_directory`. |
| **Callers / importers** | `app/main.py` (startup schema ensure); `app/core/module_resolver.py` (imports `Feature, features`); `app/modules/admin_console/router.py` (admin CRUD endpoints); `app/modules/role_ui/router.py` (role-based feature checks). | `app/main.py` line 1870 (registers `FeatureFlagMiddleware` at app startup); `app/main.py` lines 2825, 2837, 2847 (legacy admin endpoints for getting/setting/toggling `FeatureFlags` directly). |
| **Tests** | `tests/test_features.py` — 19 tests, all passed in this run. | No direct tests found in `tests/`. Middleware behavior is exercised only at integration/runtime level. |
| **Last 5 `git log --follow` commits (main)** | `d914a505`, `1019e02d`, `163820f9`, `ae734488`, `da3e44f0` | `386ed278` only — single commit, older. |
| **Pilot diff vs main** | Cosmetic + removes SQLite/utc_now compatibility, reverts `allowed_roles` JSON parsing. Same functional surface. | None — file is byte-for-byte identical on `adr-0008-pilot`. |
| **In play?** | Yes. Active in admin UI and role-based gating. | Yes. Middleware is registered at startup and guards the path prefixes above. |

## 4. Open questions this investigation could not answer

1. **Which `context_loop` is the intended runtime SSOT?** The HTTP router and startup wiring use the module copy (A); most service-to-service reads and document-pipeline writes use the service copy (B). Because each file creates its own global `ContextDataLoop()` instance, the two can diverge at runtime.
2. **What is the intended resolution for the missing methods?**
   - `app/modules/context_loop/service.py` calls `context_loop.process_input(...)` from `_on_deadline_approaching` and `_on_violation_found`, but no `process_input` method is defined anywhere.
   - `app/services/context_loop.py` is called via `context_loop.get_user_context(user_id)` from `app/services/ui_composer.py`, but no `get_user_context` method is defined anywhere.
3. **Is `data_freshness_manager` integration meant to survive?** It lives only in the service copy (B). If B is retired, does freshness validation move into A, or is it a pilot experiment to be removed?
4. **What is the migration path for callers?** Consolidating to one copy will require updating imports in `app/services/document_pipeline.py`, `app/services/case_auto_creation.py`, `app/services/adaptive_ui.py`, `app/modules/page_composer/assembly.py`, `app/core/module_hub.py`, `app/services/ui_composer.py`, `tests/test_page_composer_assembly.py`, and `tests/test_page_composer_assembly_api.py` if the service copy (B) is removed; or moving the HTTP router and startup wiring if the module copy (A) is removed.
5. **Should `app/core/feature_flags.py` be merged into `app/core/features.py`?** The two systems use different flag namespaces, different storage models, and different consumers. A consolidation would need to decide whether to preserve the path-prefix `503` middleware behavior and whether the 6 `FeatureFlags` values should become `Feature` enum members or remain a separate route-gating layer.
6. **Are any `feature_flags` table rows actually set by `app.core.feature_flags.py`?** No writes to the DB were found in the middleware or `FeatureFlags` class, so the table is populated only by `features.py` callers and startup seeding. It is unclear whether the path-based middleware is intended to be the long-term gating mechanism or legacy scaffolding.

## 5. No recommendation

This brief presents facts only. The decision whether to (a) keep one `context_loop` and delete the other, (b) split their responsibilities permanently, (c) merge `feature_flags.py` into `features.py`, or (d) leave the dual systems as-is is a product/architecture call for Brad. No "winner" is implied above.
