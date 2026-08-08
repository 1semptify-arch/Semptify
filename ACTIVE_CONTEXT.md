# Semptify Active Context

**Last Updated**: 2026-08-08 (todo-048 resolved: no await on sync token calls, no wrong db argument)

## ✅ Completed 2026-08-08 Session

### Session — todo-048 resolved: no `await` on sync `get_valid_token_for_user`, no wrong `db` argument

- **Task**: Fix incorrect `await` on non-async `get_valid_token_for_user()` calls and wrong `db` argument in `court_forms/router.py:194` and `intake/router.py:536`
- **Status**: Resolved — no code changes needed; both call sites already use `app.core.auto_refresh.ensure_valid_token(user_id, db)` correctly
- **Call sites confirmed clean**:
  - `app/modules/court_forms/router.py` form-fill overlay path: `await ensure_valid_token(user.user_id, db)`
  - `app/modules/intake/router.py` upload/auto fallback: `await ensure_valid_token(user_id, db)`
  - Original task line numbers were stale (now point to `base64.b64encode()` and `ensure_valid_token()`)
- **Regression test additions**: `tests/test_async_token_calls.py`
  - `test_no_await_on_sync_token_helpers()` — fails on `await get_valid_token_for_user(...)` or similar
  - `test_sync_token_helpers_not_called_with_db_argument()` — fails on `get_valid_token_for_user(user_id, db)` (wrong signature)
  - Verification: 3 passed
- **Todo tracking updated**: `todo-048` marked resolved in `new_audit_tasks.json`, `docs_todos.json`, `agent_orchestrator_tasks.json`

### Session — todo-047 resolved: sync token calls migrated out of async routes

- **Task**: Fix stub-detection logic in `tools/sync_orchestrator.py` (historical queue wipe: 171 → 16 tasks)
- **Status**: Resolved — protection already in place
- **Root cause**: Historical wipe at commit `a41b98c7` was due to missing `carry_forward_previous_tasks()` in original `sync_orchestrator.py`
- **Current protections verified**:
  - `carry_forward_previous_tasks()` present (line 312) — preserves existing queue when sources return empty
  - Belt-and-suspenders guard (lines 317-324) — raises `SyncError` if queue would be emptied
  - `tools/hooks/pre-commit` exists but is **not active** (`git config core.hooksPath` not set)
- **Verification**: Ran `sync_orchestrator.py` with venv311 — stub_detector returned 0, but queue preserved at 61 tasks
- **Todo tracking updated**: `todo-045` marked resolved in `new_audit_tasks.json`, `docs_todos.json`, `agent_orchestrator_tasks.json`

### Session — todo-047 resolved: sync token calls migrated out of async routes

- **Task**: Migrate sync `get_valid_token_for_user()` calls out of `async def` routes (Known Failure Registry #19)
- **Status**: Resolved — no code changes needed; all target call sites already use `app.core.auto_refresh.ensure_valid_token()`
- **Files confirmed clean**:
  - `app/main.py:4288` (media capture fallback)
  - `app/modules/voice/router.py:58` (keep-audio upload)
  - `app/modules/workflow/router.py:114` (timeline cloud load)
  - `app/modules/document_center/router.py:97,702,780,1116` (overlay, document content, update type, share)
  - `app/modules/filedored/router.py:64,133,175,247` (process, check folders, browse, list)
  - `app/services/duplicate_detection_service.py:35,140`
  - `app/modules/packet_builder/service.py:61,314`
- **Regression test added**: `tests/test_async_token_calls.py`
  - Scans `app/` for `async def` functions
  - Fails if any calls `get_valid_token_for_user(`, `token_manager.get_valid_token(`, `token_manager.validate_token(`, or `token_manager.refresh_token_if_needed(`
  - Verification: 1 passed
- **Todo tracking updated**: `todo-047` marked resolved in `new_audit_tasks.json`, `docs_todos.json`, `agent_orchestrator_tasks.json`

## ✅ Completed 2026-08-07 Sessions

### Session — Playwright suite fixed: 52 pass, 4 skip, 0 fail

- **`navigation_consistency.spec.js` rewritten** to match actual Jinja2 template structure:
  - `nav.core-nav` → `nav.header__nav` (actual `base.html` class)
  - Paths `/home.html` → `/home` (route paths, not static files)
  - Separate handling for `gui/base.html` pages (`/help` uses `nav.gui-nav`)
  - Removed mobile drawer/hamburger tests (no such elements exist)
  - 26/26 navigation tests pass (was 3/48)
- **`live_*` tests fixed** — wrapped in `test.describe` with `test.skip` unless `SEMPTIFY_LIVE_TESTS=1`:
  - `live_capability_seeding.spec.js`: conditional `pg` import (only if `DATABASE_URL` set)
  - `live_case_persistence.spec.js`, `live_upload_timeline.spec.js`, `live_migration_verification.spec.js`: same skip pattern
  - `pg` added as dev dependency in `package.json`
- **5 standalone test scripts deleted** (1,915 lines removed):
  - `smoke_test.js`, `playwright_full_system_test.js`, `navigation_consistency_test.js`, `comprehensive_ssot_audit.js`, `user_flow_continuity_test.js`
  - These used `require('playwright')` (not `@playwright/test`), weren't picked up by `npx playwright test`, and had stale `.html` path expectations
- **Commits**: `34985b98` (test fix), `8813f61b` (BUILD_STATE update)
- **Verification**: Full Playwright suite — 52 passed, 4 skipped, 0 failed (1.0m runtime)

### Session — TIER 2/3 audit cleanup

- **Datetime linting**: `datetime-lint.yml` workflow updated to grep for `datetime.now(` (broader enforcement of `utc_now()`)
- **`print()` removal**: 41 instances reviewed in `app/`; one debug `print()` removed from `app/core/error_handling.py` (logger.error already handled it)
- **CRLF normalization**: `.gitattributes` verified correct — LF for most files, CRLF for Windows batch files; Git auto-normalization working as intended
- **Hardcoded `ssot_redirect` URLs**: Reviewed — `ssot_redirect()` validates paths via `navigation.resolve_path()`, so hardcoded paths through this wrapper are SSOT-compliant
- **Duplicate file resolution**:
  - `app/services/vault_engine.py` deleted (byte-identical duplicate of canonical `app/modules/vault_engine/service.py`)
  - `scripts/filedored.py` v1.0.0 deleted (superseded by `.devin/workflows/filedored_semptify_folder_and_filer.py` v5.0.0)
  - Scratch/backup files removed: `app/core/Untitled-1.txt`, `static/onboarding/select-role.html.bak`, `static/onboarding/storage-select.html.bak`
- **`sync_orchestrator.py`**: guard added against accidentally emptying the orchestrator queue
- **Crawler scripts reviewed**: `scripts/eviction_crawler.py` and `scripts/mn_court_crawler.py` serve different purposes — both kept
- **Commits**: `c2d659a6` (TIER 2), `19a27fa8` (filedored removal), `1e65ba44` (TIER 3 BUILD_STATE)

## 🎯 Current Priority

All TIER 2/3 audit items and Playwright suite fixes are complete. The codebase is clean and the full Playwright suite runs green (52 pass, 4 skip, 0 fail).

### Next steps (when ready)

- Run `live_*` tests interactively with `SEMPTIFY_LIVE_TESTS=1` against staging when OAuth is available
- Consider adding more `.spec.js` tests for modules that currently lack coverage
- No active build task — awaiting next priority from Brad

---

## ✅ Completed 2026-08-01 Session

- **Task 6 i18n completion pass**: added public `GET /api/i18n/locale` and `POST /api/i18n/set-locale` endpoints, wired a reusable `locale_selector.html` component into `public_base.html`, `gui/base.html`, `base.html`, and `index.html`, and set the `<html lang>` attribute from the resolved locale.
- Added `get_locale` to the Jinja2 global context so templates can resolve the active locale.
- Added `/api/i18n/` to `PUBLIC_PREFIXES` (storage middleware) and `EXEMPT_PATHS` (checkpoint middleware) so the language switcher works without a storage session.
- Added Spanish UI strings for the language selector (`es.json`).
- Updated `tests/test_i18n.py` with endpoint tests for locale read, set-cookie/redirect, and invalid-locale rejection.
- Verification: `python -m py_compile` on changed files PASS; `pytest tests/test_i18n.py -q --no-cov` 14/14 passed; `pytest tests/test_ssot_architecture.py -q --no-cov` 8/8 passed; `pytest tests/module_health -q --no-cov` 122/122 passed.

## ✅ Completed 2026-07-29 Session

## ✅ Completed 2026-07-29 Session

- Implemented a generic, registry-driven module health-check framework (`tools/module_health.py`).
- Generated 115 `tests/module_health/test_<id>.py` regression tests covering module import, router presence, duplicate routes, and admin public-route exposure.
- Updated `tools/module_registry.yaml` so 114 modules have real `health_check` / `test_suite` entries.
- Flagged 7 modules with `flag_reason` (`vault_sync` on hold, `filedored` and `housing_accountability` pending Brad's swe-1.7 decision, 4 optional missing routers).
- Fixed `tools/verify_modules.py` to run per-module tests with `--no-cov` so the repo-wide `cov-fail-under=40` does not mask health results.
- Fixed `app/modules/document_delivery/router.py` duplicate `GET /api/delivery/inbox` route by moving the HTML page endpoint to `/inbox/page`.
- Verification: `pytest tests/module_health -q --no-cov` (115 passed), `tools/verify_modules.py --sync` (114 ok), `sync_orchestrator`, `guardrail_engine` all pass.

## 🎯 Current Priority: Master Handoff — B1 Admin Hub Stub Tiles COMPLETE

- `system_health` (Tier 0) — ✅ complete.
- `run_modules` (Tier 1) — ✅ complete.
- `correspondence` (Tier 2 wiring pass, PII-free) — ✅ complete.
- `user_concerns` (Tier 2 wiring pass, PII-free) — ✅ complete.
- `advanced` (Tier 1/T0; `detect_repeated_fees` cost-guard only) — ✅ complete.

B1 is done.

## 🎯 Current Priority: B2 `dispute_tracker` + B3 `eviction_timeline` greenfield build

### Done in this session
- Core `FunctionGroupContract` extended with `tier`, `allowed_routes`, `allowed_prefixes`.
- B2 Commits 1–3: `dispute_tracker` scaffold, product manifest + registry, T2 contracts, `DisputeRecord` and `ComparisonEntry` data models + schemas.
- B3 Commits 1–3: `eviction_timeline` scaffold, product manifest + registry, T2 contracts, `EvictionTimelineEvent` data model + schemas.
- PII is stored in overlay pointers, not PostgreSQL, per the DB boundary rule.
- `subject_id` is a placeholder (no FK) pending the accountability_ledger boundary decision (Option 3).

### Done in this session (continued)
- B2 Commit 4 — minimal GUI: `GET /api/dispute-tracker/` page, `POST /api/dispute-tracker/disputes`, `POST /api/dispute-tracker/comparisons`.
- B2 Commit 5 — `FunctionGroupContract` allowed_routes aligned with actual routes.
- B3 Commit 4 — minimal GUI: `GET /api/eviction-timeline/` page, `POST /api/eviction-timeline/events`.
- B3 Commit 5 — `FunctionGroupContract` allowed_routes aligned; `tools/checks/contract_route_check.py` guardrail added (Build Orchestrator hard-gate) and passes.
- Post-GUI SSOT fix: all POST redirects use `ssot_redirect()` instead of raw `RedirectResponse`.
- `tools/checks/contract_route_check.py` enforces tier validity, manifest-prefix coverage, actual route-to-contract matching, and `PUBLIC_PREFIXES` exposure (only T0 routes may be public).

### Still pending / open
- T2 tier for `dispute_tracker` and `eviction_timeline` is flagged in commit messages for Brad's review.
- `EvictionTimelineEvent.subject_id` remains a placeholder (no FK) pending accountability_ledger boundary.
- Live manual test of the HTML pages has not been run (only `verify_modules`, `guardrail_engine`, and `pytest` passed).

---

## 🎯 Current Priority: Trauma-Informed UX + Admin/Logging + Input/Import/Resource Directory

Master Handoff promoted from `temp/Semptify_MASTER_HANDOFF.md`, consolidating:
- `temp/Semptify_TraumaInformed_UX_Admin_Spec.md`
- `temp/Semptify_Input_Import_Resource_Spec.md`

Scope: 11 build tasks across shared UX foundation, footer/help content, voice-to-text,
multi-language, mobile media capture, third-party contact model, asymmetric redaction,
communication import pipeline, and resource directory. All tasks are tenant-side,
public-service, and follow the four-pillar model (RECORD/KNOW/ACT/GOVERN).

Task 1 — Shared UX foundation — is complete (viewport-locked CSS, function-budget classes,
persistent "Get help now" in `gui/base.html`, calm/alarm color tokens, convention documented).

Task 2 — Footer + Help page redo — is complete. Shared Jinja/public/static footers and the
unified footer loader now show a one-line UPL boundary, "Get help", and "Report a problem" only.
`/help` is a no-scroll, action-first page routed by "What's happening to you right now?" into
RECORD / KNOW / ACT / GOVERN.

Task 3 — Content pass — is functionally complete. `app/core/subject_starters.py`, the reusable
starter-chips component, and the previous `free`-wording audit are in `main` (commit `8e58602b`).
This session added an action-first rewrite of `app/templates/public/portal.html` with a concrete
tenant-rights fact in place of an inspirational quote.

Master Handoff Tasks 4-11 are reconciled with the working tree:
- 4 Admin/logging: middleware + buffered flusher + live tail and level endpoints wired.
- 5 Voice: `/api/voice/transcribe` route and module health pass.
- 6 i18n: catalog files and Jinja `_()` global wired.
- 7 Media capture: `/tenant/capture` page, `/api/tenant/capture`, `/api/media/capture` wired.
- 8 Third-party contacts: `ThirdPartyContact` model + `contacts` router; module health pass.
- 9 Redaction: `redaction_service` wired into `intake_service` before storage.
- 10 Communication import: `.eml`/`.mbox`/SMS/call-log/voicemail flows; module health pass.
- 11 Resource directory: public/admin routes, CSV import, staleness tracking; module health pass.

### Live verification blockers fixed

- `app/core/storage_middleware.py`: added `/api/resources` to `PUBLIC_PATHS` and `/api/resources/` to `PUBLIC_PREFIXES`. `GET /api/resources` now returns 200 instead of 401.
- `app/core/checkpoint_middleware.py`: added `/portal` to `EXEMPT_PATHS`.

### Root landing / portal wiring

Implemented the hotel analogy:
- `/` (lobby) — `app/templates/index.html`, stateless composer, fixed CSS and CTAs to `/preamble` (app entry) and `/portal` (concierge).
- `/portal` (concierge) — `app/templates/public/portal.html` with the services catalog; now a registered `PortalPage` and public in both `storage_middleware` and `checkpoint_middleware`.
- Floors — existing `/gui/*`, `/tenant/*`, standalone modules, etc.

### Remaining blocker before assembly

- Missing `feature_flags` DB table — causes fallback warnings but does not block public pages or the reconciled modules.

Next: GUI/site assembly.

Previous priority: Review/merge Funding Forge standalone add-on — completed 2026-07-25.
Previous priority before that: GUI Phase 1 — four-pillar interface (`Home`, `Record`, `Know`, `Act`).

## ✅ Completed 2026-07-25 Session

- **Funding Forge add-on** — standalone package `funding_forge/` with FastAPI backend, async SQLAlchemy models, full CRUD JSON API, SPA GUI, document uploads, admin-only auth, optional Cloudflare R2 document storage, and 33 pre-seeded suggested funding entities. Tests pass.
- **Document Center gap fill** — persisted field confirm/correct state via `VaultReviewState`, user-controlled verification status, real document sharing via `DocumentShare`, old `documents.html` pages redirected to `/dc`, and frontend wiring in `document_center.html` to load/save state and create share links. Backend and integration tests pass; full live browser viewer verification pending storage-connected onboarding.

## ✅ Completed 2026-07-19 Session

- **Icon replacement policy applied**: 5 GUI templates + `document_center.html` now use
  minimal unicode markers (`▸`, `◆`, `●`, `○`) instead of emoji. Functional status markers
  (`✕`, `↗`) preserved.
- **Sync-orchestrator hook loop fixed**: root cause was CRLF writes + non-idempotent
  timestamps. All sync-chain Python scripts now use `newline="\n"` + trailing newline +
  only-write-if-changed.
- **Document Center verified live**: 22 DC tests pass, 3-pane layout live at
  `/tenant/documents`, OAuth-gated as expected.
- **DC Slice 2+ complete**: viewer rendering wired to real vault data (`/api/dc/document/{id}/view`), unlock pattern panel uses `/api/dc/unlocks`, all `alert()`/`prompt()` removed from `document_center.html` in favor of `SemptifyFeedback` + non-blocking `showValueModal()`.
- **Calendar total-recollection viewer complete**: `calendar.html` now pulls the full `GET /api/calendar/` timeline, groups events by month, and uses minimal unicode markers for event type icons.
- **Timeline interactive query viewer complete**: `timeline.html` now wires search, date-axis, item-type, urgency, evidence-only, and date-range filters to `POST /api/timeline/unified`; all emoji icons and `alert()` fallbacks removed.
- **Comms Log complete**: `comms_log.html` and `GET /comms-log` route added; logs are stored as `event_type='communication'` timeline events and displayed on `/comms-log`.
- **MNDES todo-021 unblocked**: `MNDESRestClient` speculative REST implementation added; related `MNDESExhibitPackage`/`MNDESExhibitService` model and serialization bugs fixed; `tests/test_mndes_service.py` passes 19/19.
- **Visual smoke test passed**: all 4 public GUI pages verified on live deploy.
- **Attorney Intake Packet rendering + GUI trigger**: PDF/ZIP export endpoints added to
  `app/modules/case_builder/router.py`, download UI added to `case_builder.html`,
  `test_intake_packet.py` updated with 3 new helper tests, all 21 tests pass.

## 🅿️ NEXT TO BUILD (in priority order) — Master Handoff

| # | Project | Design Doc | Status | Blocked By |
|---|---------|------------|--------|------------|
| 1 | **Shared UX foundation** — viewport-locked desktop template, function-budget convention, persistent "Get help now" component, calm/alarm CSS tokens | `Semptify_MASTER_HANDOFF.md` section A–B | ✅ Complete | — |
| 2 | **Footer + Help page redo** — trust-signaling footer, "What's happening to you right now?" Help page | `Semptify_MASTER_HANDOFF.md` Task 2 | ✅ Complete | — |
| 3 | **Content pass** — welcome/about plain-language rewrite, words of wisdom moved to About only, subject starters | `Semptify_MASTER_HANDOFF.md` Task 3 | ✅ Complete | — |
| 4 | **Admin/dev access + logging** — Tailscale-gated admin, JSON logging, R2 async flush, live tail, feature flags, health/status page | `Semptify_MASTER_HANDOFF.md` Task 4 | ✅ Complete | — |
| 5 | **Voice-to-text** — Web Speech API client-side default, Whisper fallback with raw-audio discard | `Semptify_MASTER_HANDOFF.md` Task 5 | ✅ Complete | — |
| 6 | **Multi-language i18n** — JSON/.po catalogs, human-reviewed legal/plain-language translation | `Semptify_MASTER_HANDOFF.md` Task 6 | ✅ Complete | Human review of 13 stub catalogs pending |
| 7 | **Mobile media capture** — `getUserMedia` photo/audio evidence capture with recording-consent note | `Semptify_MASTER_HANDOFF.md` Task 7 | ✅ Complete | Browser permission UX pending live device test |
| 8 | **Third-party contact model** — `ThirdPartyContact` table, case-linked, entity types, audit source | `Semptify_MASTER_HANDOFF.md` Task 8 | ✅ Complete | — |
| 9 | **Asymmetric redaction pass** — strip user's own PII while preserving third-party info from imports | `Semptify_MASTER_HANDOFF.md` Task 9 | ✅ Complete | — |
| 10 | **Communication import pipeline** — `.eml`/`.mbox`, SMS CSV/XML, voicemail audio→transcription→discard, call logs CSV | `Semptify_MASTER_HANDOFF.md` Task 10 | ✅ Complete | — |
| 11 | **Resource directory** — `Resource` table, bulk CSV import, staleness tracking | `Semptify_MASTER_HANDOFF.md` Task 11 | ✅ Complete | Admin UI not yet built; endpoints are API-only |

> **Open decisions before Tasks 4/6/9–10 can be fully scoped:**
> 1. ✅ Log retention window — **90 days rolling** (resolved 2026-07-26).
> 2. ✅ Confirmed language priority list — English, Spanish, Somali, Hmong, Arabic, Amharic, Tigrinya, Mandarin, French, German, Korean, Japanese, Portuguese, Italian.
> 3. ✅ Redaction matching strategy — user-known contact info plus heuristic PII detection with a `ThirdPartyContact` allowlist.

### ✅ Completed (reference, not to-do)
- Funding Forge — complete 2026-07-25.
- UPL guardrail wiring — complete 2026-07-10.
- GUI Phase 1 — complete 2026-07-19.
- Document Center — 22 tests pass, live at `/tenant/documents`.
- Attorney Intake Packet — complete 2026-07-19.
- Journal, Rent Ledger, Packet Builder — complete 2026-07-20.

## 🎯 Candidate Next Priorities (awaiting user direction)

- **Packet Builder UI** ✅ — four-pillar GUI panel shipped 2026-07-28 and live-tested with Google Drive; todo-044 complete.
- **Semantic Context Engine (Deep OCR Pass 2)** — `todo-036` resolved 2026-07-28; rule-based engine + acceptance tests + async token refresh in deep OCR job.
- **Litigation Intelligence graph endpoints** — `todo-020` resolved 2026-07-28; graph engine and build/visualize/path endpoints already live and tested.
- **Orchestrator todo sweep** ✅ — `todo-021` through `todo-032` resolved 2026-07-28.
- **Next `swe-1.7` candidates** — `todo-022` (housing_accountability detect_repeated_fees) and `todo-024` (filedored_service classification) are now hardened and resolved.
- **vault_sync** — ON HOLD per user 2026-07-01. Plan captured in memory.

### Action Feedback Helper — COMPLETE
All 13 retrofittable pages now use `SemptifyFeedback.*` directly. No `alert()` fallbacks
remain. Helper is globally loaded via `feedback.js` in `base.html`.

### GUI Phase 1 — Four-Pillar Interface Model
The user-facing GUI is organized around the four-pillar model defined in
`docs/admin/Semptify_Site_GUI_Framework.md`:
- **RECORD** — capture and organize evidence (Vault, Timeline, Document Center, Calendar, Journal, Comms Log, Rent Ledger, PDF Tools)
- **KNOW** — facts only, no opinions (Library, State Laws, Context Engine, RISC, Court Case Lookup, Search)
- **ACT** — lawful, guided action (Case Builder, Eviction Defense, Court Forms, Complaint Wizard, Plan Maker)
- **GOVERN** — platform integrity (Admin Console, Forge, Capabilities, Onboarding, Auth, Audit Logs)

The older 2026-06-28 Journal/Calendar/Timeline vision is superseded by this framework.
Each RECORD feature still does the same work (Journal captures, Calendar shows all
events, Timeline queries data), but now sits inside the four-pillar structure.

### Document Center — IMPLEMENTED
Design docs in `docs/planning/`, implementation in `app/modules/document_center/`.
3-pane layout (vault list / viewer / overlays), 5 actions (upload/store/process/review/share),
per-document-type checklists, verification states, unlock pattern. Slice 2+ wired the viewer
and unlock panel to live vault data. 22 tests pass.

---

## 🚫 Anti-Priorities (Don't Start These)

> **Exception for this session:** the Master Handoff tasks below are explicitly promoted
to active priority, overriding the "no new features" rule for this scope only.
> This exception is recorded in the Decision Log.

1. **Refactoring** unrelated to the Master Handoff tasks
2. **Documentation** that isn't critical path for the Master Handoff
3. **Testing** of non-core systems
4. **New features outside the Master Handoff scope**

---

## 📋 Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-07-26 | ✅ Log retention window set to 90 days rolling | Default recommended in `Semptify_TraumaInformed_UX_Admin_Spec.md`; balances operational troubleshooting needs against unbounded R2 storage growth. Task 4 admin/logging can now scope R2 lifecycle policy and async flush with a fixed window. |
| 2026-07-25 | ✅ Master Handoff promoted to active priority (11 tasks: UX foundation, admin/logging, voice, i18n, media capture, contacts, redaction, import pipeline, resource directory) | User explicitly promoted `temp/Semptify_MASTER_HANDOFF.md` to active priority; recorded in this file. Anti-priority "no new features" temporarily lifted for this scope only. Three open decisions (retention, language list, redaction strategy) still need resolution before full scoping. |
| 2026-07-10 | ✅ Superseded 2026-06-28 GUI vision (Journal/Calendar/Timeline) with four-pillar model (RECORD/KNOW/ACT/GOVERN) | Framework formalized across a full planning session; GUI Screens 1-3 (nav shell, home, record) already shipped under new model. See `docs/admin/Semptify_Site_GUI_Framework.md` for the canonical pillar definitions. |
| 2026-06-30 AM | ✅ Action Feedback helper retrofit complete | 13 pages retrofitted. All `alert()` fallbacks removed. `SemptifyFeedback` is globally loaded, so `if (window.SemptifyFeedback)` guards and `else { alert() }` branches were dead code. Also added success toast to journal save (was silently succeeding). |
| 2026-06-29 PM | ✅ Repo cleanup — 108 obsolete docs archived | Reduce doc sprawl from 130+ to ~40 active docs. All obsolete docs moved to `archive/obsolete-2026-06-29/` with git history preserved. |
| 2026-06-29 PM | ✅ Filedored overlay integration fixed | 3 callers now wire overlay_manager. Router signature bugs fixed. Commit `19d0860`. |
| 2026-06-24 PM | ✅ Context Engine + Page Composer complete | 9+3 endpoints live, 4 consumers wired, migration shipped (commit 375b45d) |
| 2026-06-24 PM | ✅ Context Engine wired into 4 consumers | Case Builder, Complaint Wizard, Tenant Defense, Page Composer |
| 2026-06-24 | ✅ Phase 4 role development complete | All 6 roles have full endpoint coverage |
| 2026-06-24 | ✅ Litigation Intelligence activated | Fixed dataclass field ordering bugs, 17 endpoints live |
| 2026-06-24 | ✅ Advocate dashboard added | GET /api/advocate/dashboard with aggregate stats |
| 2026-06-21 | ✅ Completed audit + design docs | STATUS_AUDIT.md, ACTION_FEEDBACK_AUDIT.md written |
| 2026-06-21 | ✅ Context Engine design captured | PostgreSQL cache, stories after task, avoided_court hero |
| 2026-06-21 | ✅ Action Feedback design captured | SemptifyFeedback helper, 5-tier retrofit |
| 2026-06-21 | Start Phase 4 — Role Development | Audit complete, ready to fix stubs |
| 2026-06-04 | Reconnect session persistence fix | DB-first session save |
| 2026-04-21 | Completed Communication System | Document fill/sign + messaging + vault storage |
| 2026-04-21 | Completed Unified Overlay System | All components integrated |

---

## 🔗 Quick Links (canonical docs only)

- **Project Bible**: `PROJECT_BIBLE.md` — governance + doc hierarchy
- **Build Status**: `BUILD_STATE.md` — live deploy state
- **Status Audit**: `STATUS_AUDIT.md` — 2026-06-21 module snapshot
- **Stub Audit**: `STUB_AUDIT.md` — 2026-06-19 TODO/stub inventory
- **Action Feedback Audit**: `ACTION_FEEDBACK_AUDIT.md` — Phase 5b design
- **GUI Framework**: `docs/admin/Semptify_Site_GUI_Framework.md` — canonical four-pillar model (RECORD/KNOW/ACT/GOVERN)
- **Roadmap**: `ROADMAP_TO_PUBLIC_RELEASE.md`
- **Blueprint**: `BLUEPRINT.md`
- **System Manifest**: `SEMPTIFY_SYSTEM_MANIFEST.md` — module registry
- **Build Guide**: `BUILD_GUIDE_SSOT.md`
- **Deployment**: `DEPLOYMENT_READINESS.md`
- **Security**: `SECURITY_AND_PRIVACY_ARCHITECTURE.md`
- **Vault Paths**: `app/core/vault_paths.py`

---

*This file is the single source of truth for what is being worked on RIGHT NOW.*
