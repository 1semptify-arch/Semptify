# Semptify Active Context

**Last Updated**: 2026-08-22 (Notice Date → Received Date tenant-facing rename complete; Render MVP Dockerfile already verified; next: three-date sort/view verification, attorney invite-code stub)

> Standing rule: see `.devin/rules/10-progressive-disclosure.md` for the **Progressive Disclosure / Capability Revelation** rule (companion to the GUI Design Rule and Navigation Principle).

> Standing rule: see `.devin/rules/10-progressive-disclosure.md` for the **Progressive Disclosure / Capability Revelation** rule (companion to the GUI Design Rule and Navigation Principle).

## Philosophy

- **Motive:** get the user the answer to their problem as fast as possible — whether that answer comes from Semptify or from pointing them to another entity entirely. No cost to the user, ever.
- **Backstage narration exists for one reason:** to keep a user's attention and reduce anxiety during real waiting. Once something is instant and reliable, narrate less or not at all.
- **Users shouldn't have to think about how Semptify works.** Simple, easy, quick, painless. Complexity is justified only by a real wait or a real decision point.

## Sequencing — simplify first, add later (the actual current priority)

1. ~~Finish the single preview in progress (`journal_create`, RECORD pillar).~~ DONE — verified, polished, passed eye-judgment.
2. ~~Judge it by eye.~~ DONE — failed first pass, polished, passed second pass.
3. ~~Repeat the pattern for one more function, different pillar, to confirm generalization.~~ DONE — `law_library_get_statute` (KNOW pillar) passed clean on first try, no polish round needed. Pattern confirmed to generalize across write/save vs. read/lookup shapes.
4. ~~One more generalization test — ACT pillar.~~ DONE — `eviction_defense_calculate_deadlines` proved the pattern holds even with GOVERN/UPL risk-tier involvement (consequence notice + legal disclaimer on the same screen, no runtime suppression needed).
5. ~~Build the real tapering dial, wire Module Resolver, add form-factor layout variants.~~ DONE — Familiarity Tapering (`intensity_level`/`exposure_count`) live, Module Resolver wired (non-blocking notice pattern), desktop-poster/mobile-stacked-scroll variants applied to all three templates, Page Shell CSS/token vocabulary applied for visual consistency with Concierge pages. Verified at 375px and 1280px, all checks clean.
6. **Current step: pause point.** All three tenant-facing pillars (RECORD, KNOW, ACT) have a proven, verified, responsive, visually-consistent single-function guide page. This is a real, demoable slice of the app. The next item on the list is the PageEngine facade — but that's new infrastructure, not a repeat of a proven pattern, and it's invisible to users. Recommend pausing architecture work here rather than continuing straight into it. Decide next based on what's actually needed: more functions using this pattern, real use/demo of what exists, or the facade — in that order of likely value.

## Backlog (not urgent, tracked centrally — do not fix per-function)

- **Contract copy is too technical for user-facing display** (e.g., "Law Library Get Statute (SSOT)", "CANONICAL detailed view..."). Templates already expose title/description override blocks, so this is a copy pass, not a contract change — but it should happen once, centrally, across all functions, not patched ad hoc per page as it's noticed.

## Core Rules (current, corrected)

- **One function, one page — as the default, not an absolute mandate.** Applies whenever a user could reasonably arrive at that function on its own (menu, search, next-step link) — journal entry, statute lookup, deadline calculator, all correctly single-function pages, all proven.
- **Function GROUPS get their own page-flow when steps are strictly sequential and meaningless in isolation** — nobody looks up step 2 of onboarding without step 1. Test: would a user ever return to this step alone, out of sequence? If yes, separate function page. If no, it belongs in a group, still one decision per screen, just chained as one recognized task instead of scattered destinations. Onboarding (welcome → role select → storage OAuth → tenant home) is the clear first candidate for this pattern — not yet built, noted for when it's needed.
- **Header and footer are fixed, universal templates.** Never vary by page.
- **Four body layout types, one per pillar:** Record / Know / Act / Govern. Every single-function page uses exactly one.
- **Access is never gated by mastery.** If a user's situation requires a function, it's available — full stop.
- **Familiarity Tapering governs density only** — narration and UI chrome, not availability. Uses ADR-0008's `intensity_level`: Off / Subtle / Standard / High.
- **Two independent page models, not competing:**
  - Page Composer + Page Shell (existing, unchanged) — blended multi-pillar pages, owns Concierge/dashboard/landing/library-browse. Confirmed sound — matches existing code (`assembly.py`, `/gui/dashboard`, `/gui/page/{subject}`, `/tenant/library` subject pages).
  - UI Composer, extended — strict single-function pages, one pillar, no blend. Owns in-task guide pages. Confirmed sound — matches `/gui/record/journal/create` using `record_body.html`.
  - They share Context Loop, `module_contracts.py`, and will eventually share the Information Orchestrator, but never render the same kind of page.
- **Page Shell CSS token decision (applied):** the three UI Composer body templates (`record_body.html`, `know_body.html`, `act_body.html`) reuse Page Shell's CSS tokens/class vocabulary (zone/block/output-trigger patterns) for visual consistency across both page families — but not its 4-pillar grid, skeletons, channels, blends, or GOVERN logic.

## Current Build Status

- **Verified and complete:** three in-task guide previews:
  - `journal_create` (RECORD) — write/save
  - `law_library_get_statute` (KNOW) — read/lookup
  - `eviction_defense_calculate_deadlines` (ACT) — guided calculation, UPL-risk output
- All use `body/{pillar}_body.html`, contract-driven I/O, real `intensity_level`/`exposure_count` from the Experience Token (no longer hardcoded `tapering_tier="new"`), form-first layout, one next-step lead-in, calm `Get help now` CTA, optional density behind `<details>`, desktop-poster / mobile-stacked-scroll form-factor variants, and Page Shell CSS/token vocabulary.
- **Local dev auth bypass added:** `POST /debug/seed-test-user` now creates a fake tenant, sets the signed `semptify_uid` cookie, and redirects to `/gui/record/journal/create`. Verified end-to-end: save journal, look up statutes, calculate eviction deadlines — all return 200 in local dev without real OAuth.
- **Page Composer inventory completed (read-only):** full survey of `app/modules/page_composer`, `app/modules/page_shell`, `app/services/ui_composer`, callers, contracts, templates, and consumers. Key findings: Page Composer and Page Shell `register.py` contracts are not in `app/core/contract_loader.py`; Page Shell is production-exposed through Page Composer despite its `dev_only` manifest lifecycle; the assembly capability filter is currently a no-op.
- **Page Composer / Page Shell prioritized cleanup completed:** all six inventory gaps addressed — capability filter wired to resolved module paths with `block.module_name`; `case_builder.get_cases_for_user` implemented and used; Page Shell manifest promoted to CORE (renderer is production, /api/page-shell routes stay admin); Page Composer + Page Shell contracts loaded by `contract_loader.py`; mobile CSS confirmed non-clipping; assembly formula blueprint promoted from DRAFT to APPROVED.
- **Fourth single-function guide page built:** `/gui/record/timeline/create-event` for `timeline::timeline_create_event`. Reuses the proven pattern (record_body.html, Page Shell tokens, tapering, resolver notice, form-first layout, next-step CTA). Verified real use with a live `POST /api/timeline/events` save and 375px scroll.
- **Context Explanation Workbook + Loader:** created `docs/context_explanation_workbook.md`, `docs/context_explanation_needs.md` (human-readable checklist with context-of-use for all 56 combinations, high-priority starter set first), `data/explanation_workbook_template.csv`, `data/explanation_workbook_example.csv`, `data/context_explanation_workbook.csv` (full 56-row workbook with placeholder prompts), and `tools/load_explanation_workbook.py`. Loaded 3 example entries; `context_explanation_entries` is no longer empty. Editorial work can now proceed without engineering.
- **Confirmed/resolved, no action needed:**
  - Page Composer does not bypass UI Composer — orchestrates above it.
  - Context Loop ≠ Information Orchestrator — complementary, not duplicate.
  - Two-page-model resolution — confirmed sound.
- **Logged, not urgent, do not fix yet:**
  - Case Builder phantom function (`get_cases_for_user` doesn't exist).
  - Page Shell manifest mismatch — registered dev/admin-only but used in production tenant routes.
  - ~25 modules missing `FunctionGroupContract`; no contract has GUI fields yet.

## Later: Page Engine Facade (reference only, not active work)

Once 2-3 functions are proven, the growing list of systems (Context Loop, Context Engine, Page Composer, Page Shell, UI Composer, Positronic Mesh, Module Resolver, Information Orchestrator) should sit behind one entry point — `PageEngine.render(user_id, request) → HTML` — so routes and future agents only ever call one thing. Don't build this now.

---

## ✅ Completed 2026-08-20 Session — Page Composer architecture inventory

- Read-only inventory of `app/modules/page_composer`, `app/modules/page_shell`, `app/services/ui_composer`, calling routes, templates, contracts, and tests.
- Verified live endpoints on `http://127.0.0.1:8001`: `GET /api/page/` (200, 14 subjects), `GET /api/page/repair/render` (200, Page Shell HTML), `GET /gui/page/repair` (200), `GET /api/page/eviction/preview` (200).
- Documented scope boundary: Page Composer = multi-pillar pages (dashboard, library, landing); UI Composer = single-pillar in-task guides; Page Shell = data-driven renderer.
- Noted gaps: Page Composer and Page Shell `register.py` contracts are not loaded by `app/core/contract_loader.py`; Page Shell is production-exposed through Page Composer despite its `dev_only` manifest lifecycle; capability filter is a no-op; `_gather_user_case` depends on a non-existent `get_cases_for_user`.

## ✅ Completed 2026-08-20 Session — Local dev tenant auth bypass

- Created a local `.env` (gitignored) with `SECRET_KEY`, `PORT=8001`, `SECURITY_MODE=open`, and `DATABASE_URL=sqlite+aiosqlite:///./semptify.db`.
- Fixed `POST /debug/seed-test-user` in `app/main.py`: replaced SQL `NOW()` with `utc_now()` bind parameters for SQLite compatibility, then signs and sets the `semptify_uid` cookie and redirects to the RECORD guide.
- Verified the dev tenant can use all three in-task guide pages and their save/action endpoints:
  - `POST /api/journal/` creates a journal entry.
  - `GET /api/law-library/statutes` returns statutes.
  - `POST /api/eviction-defense/calculate-deadlines` returns deadlines.
- `python -m py_compile app/main.py` PASS; `pytest tests/module_health -q --no-cov` 244 passed.

## ✅ Completed 2026-08-20 Session — ADR-0008 Layer 2 Problem A: semantic retrieval

- Implemented dialect-aware `AsymmetricVector` (`app/core/database_types.py`) using pgvector `VECTOR(384)` on PostgreSQL and JSON blobs on SQLite.
- Added `embedding` columns to `ContextExplanationEntry` and `ContextFact`; wired embedding generation into explanation entry create/update and fact upsert.
- Added `app/modules/context_engine/embedding_model.py` singleton (`all-MiniLM-L6-v2`, 384 dimensions) and `app/modules/context_engine/vector_math.py` pure-Python cosine for SQLite.
- Rewrote `app/modules/context_engine/retrieval.py` as hybrid metadata pre-filter + embedding cosine similarity; recalibrated `LAYER2_CONFIDENCE_THRESHOLD` from `0.75` to `0.45` based on realistic spot-checks.
- Added `scripts/backfill_context_embeddings.py` to backfill existing curated rows.
- Added Alembic migration `20260820_add_embedding_columns.py` with `CREATE EXTENSION IF NOT EXISTS vector;` for PostgreSQL.
- Added `sentence-transformers` and `pgvector` to `requirements.txt`.
- Verification: `python -m py_compile` on all changed Python files PASS; `pytest tests/test_information_orchestrator_pilot.py -q --no-cov` 12/12 pass; `pytest tests/module_health/test_context_engine.py tests/test_context_engine_verifier.py -q --no-cov` 7/7 pass; full `pytest tests/module_health -q --no-cov` 244/244 pass.
- Spot-checks: "late fee lease clause" returns both the late-fee entry and the semantically related penalty-charge entry; "security deposit return", "eviction notice deadline" return correct entries; unrelated "traffic ticket" returns nothing (silence beats fabrication).
- Runtime: the local Uvicorn server starts and loads the embedding model (background task) with `EMBEDDING_MODEL_LOCAL_FILES_ONLY=true`; the 2 existing `context_facts` rows have embeddings after `scripts/backfill_context_embeddings.py`.
- Open / limitation: PostgreSQL pgvector parity was not exercised locally because no live PostgreSQL environment is available; the code path is implemented and the Alembic migration creates the extension and columns. Memory on the local VM is already 92–95% before model load; the model itself adds ~25–100 MB and loads in ~3–5 s once torch/numpy are warm, but the deployment tier must have enough headroom.

---

## ✅ Completed 2026-08-19 Session — UI Composer form-factor and Page Shell alignment

- Applied the established desktop-poster / mobile-stacked-scroll pattern (900px breakpoint, CSS grid) from `dispute_tracker.html` / `eviction_timeline.html` to the three in-task guide body templates (`record_body.html`, `know_body.html`, `act_body.html`).
- Aligned the three body templates with Page Shell CSS token vocabulary (zone/block/block-input/output-trigger, level-driven shades, no card borders) while keeping them strict single-function compositions; did not adopt Page Shell's four-pillar grid, skeletons, PageConfig, channels, blends, or GOVERN logic.
- Preserved all must-not-regress behavior: form-first ordering, `user_id`/internal contract field filtering, calm `Get help now`, `<details>` progressive disclosure, Familiarity Tapering, Module Resolver non-blocking notice, and one next-step lead-in.
- Verification: `python -m py_compile` on changed Python files PASS; `pytest tests/module_health -q --no-cov` 244 passed; IronBee DevTools desktop + mobile verification for all three pages PASS (console clean, ARIA presence checks pass, ACT functional path completes); screenshots retained at `C:\Users\bradc\AppData\Local\Temp\uic-verify`.
- Task `ui-composer-formfactor-001` marked resolved. PageEngine facade remains deferred.

## ✅ Completed 2026-08-15 Session — Fact-check/freshness close-out

- Merged PRs #91, #92, #93: Phases A–D of the fact-check/freshness build.
- ADR-0009 flipped from `Proposed` to `Accepted`.
- Auto-hide decision recorded: a stale or unverifiable public claim is hidden, not shown with a placeholder or "last verified" fallback.
- `PROJECT_BIBLE.md` and `README.md` updated with references and a worked example.
- `BUILD_STATE.md` close-out entry added.

## ✅ Completed 2026-08-15 Session

- `todo-065`: migrated PAGE_MANIFEST to template-first source files (PR #86).
- `phase2-50551b-067`: verified security-router secure-cookie expressions are equivalent; preserved `main` (PR #87).
- `phase2-dc4e66-065`: verified dashboard/progress wiring; preserved `main` (PR #88).
- `main` branch ruleset `protect-main` was found misconfigured (empty `include` patterns), then updated via the GitHub API to target `refs/heads/main` and verified by a second throwaway direct push that was rejected.
- Updated `docs/AI_TEAM_OPERATING_PROTOCOL.md`, `BUILD_STATE.md`, and `ACTIVE_CONTEXT.md` with the close-out status.

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
| --- | --------- | ------------ | -------- | ------------ |
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
>
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
`Semptify_Site_GUI_Framework.md`:

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
| ------ | ---------- | -------- |
| 2026-07-26 | ✅ Log retention window set to 90 days rolling | Default recommended in `Semptify_TraumaInformed_UX_Admin_Spec.md`; balances operational troubleshooting needs against unbounded R2 storage growth. Task 4 admin/logging can now scope R2 lifecycle policy and async flush with a fixed window. |
| 2026-07-25 | ✅ Master Handoff promoted to active priority (11 tasks: UX foundation, admin/logging, voice, i18n, media capture, contacts, redaction, import pipeline, resource directory) | User explicitly promoted `temp/Semptify_MASTER_HANDOFF.md` to active priority; recorded in this file. Anti-priority "no new features" temporarily lifted for this scope only. Three open decisions (retention, language list, redaction strategy) still need resolution before full scoping. |
| 2026-07-10 | ✅ Superseded 2026-06-28 GUI vision (Journal/Calendar/Timeline) with four-pillar model (RECORD/KNOW/ACT/GOVERN) | Framework formalized across a full planning session; GUI Screens 1-3 (nav shell, home, record) already shipped under new model. See `Semptify_Site_GUI_Framework.md` for the canonical pillar definitions. |
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
- **GUI Framework**: `Semptify_Site_GUI_Framework.md` — canonical four-pillar model (RECORD/KNOW/ACT/GOVERN)
- **Roadmap**: `ROADMAP_TO_PUBLIC_RELEASE.md`
- **Blueprint**: `BLUEPRINT.md`
- **System Manifest**: `SEMPTIFY_SYSTEM_MANIFEST.md` — module registry
- **Build Guide**: `BUILD_GUIDE_SSOT.md`
- **Deployment**: `DEPLOYMENT_READINESS.md`
- **Security**: `SECURITY_AND_PRIVACY_ARCHITECTURE.md`
- **Vault Paths**: `app/core/vault_paths.py`

---

*This file is the single source of truth for what is being worked on RIGHT NOW.*
