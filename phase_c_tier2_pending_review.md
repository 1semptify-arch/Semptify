# Phase C Tier 2 — Pending Review

This file tracks files in the `adr-0008-pilot` branch that are still different from `main` and require an explicit user decision before merging. Tier A/B rulebook-matched items are being applied in separate batches.

## Pending Tier C items

### 1. `app/main.py` — partially handled in Batch 11
- **Status:** Tier B rulebook fixes applied; remaining Tier C changes still under review.
- **Applied (Batch 11):**
  - `_GOOGLE_DRIVE_FORCE_AUTH` constant + `navigation.add_escape_hatch()` registration
  - Two `utc_now()` timestamp normalizations
  - Two `ensure_valid_token()` token-refresh / `get_session_factory()` fixes
  - Hardcoded `ssot_redirect(...)` → `navigation.get_stage(...).path` for `/onboarding/start`, `/gui/dashboard`, `/tenant/dashboard`, `/tenant/home`, `/tenant/timeline`, `/documents`, `/tenant/library`
- **Still to review / decide:**
  - `/tenant/journal` page content replaced with redirect to timeline
  - `/gui/dashboard` route removal / new command-center template lookup
  - Tenant dashboard redirect to `tenant_timeline`
  - New `/index` route
  - UI Composer / page-manifest / template assembly changes (`todo-065`)
- **Overlap:** static-to-template page manifest migration (`todo-065`)
- **Recommendation:** Keep remaining `main.py` changes for the dedicated `todo-065` / page-manifest pass.

### 2. `app/core/page_manifest.py`
- **Why it is Tier C:** explicitly named in the handoff as `todo-065` scope
- **Pilot changes include:** 410-line page-manifest / template migration
- **Recommendation:** defer to `todo-065`.

### 3. `app/modules/vault/router.py`
- **Why it is Tier C:** API response shape + ADR-0008 wiring
- **Pilot changes include:** new `/envelope` endpoint returning Object/Experience Envelope JSON; token-refresh calls were already merged via PR #56
- **Recommendation:** review the `/envelope` endpoint and Experience Token wiring before merging.

### 4. `app/modules/eviction_timeline/router.py` — merged via PR #62
- **Why it is Tier C:** API response shape + ADR-0008 wiring
- **Applied (Batch 12, merged to main at `871ab345`):**
  - Redirect fix `ssot_redirect("/api/eviction-timeline/", ...)` → `ssot_redirect(navigation.get_stage("eviction_timeline_home").path, ...)`
- **Still open / deferred for ADR-0008 review:**
  - New `/momentum-checkpoint` and `/envelope` endpoints
  - `EncounterContext`, `get_eviction_timeline_page`, and `get_momentum_checkpoint` wiring
- **Recommendation:** Keep the new ADR-0008 endpoints for a dedicated review.

### 5. `app/modules/page_composer/assembly.py`
- **Why it is Tier C:** likely part of page-manifest / assembled-page flow
- **Pilot changes include:** 150-line diff around page assembly and template rendering
- **Recommendation:** review whether this is `todo-065` scope or a genuine ADR-0008 wiring change.

### 6. `app/modules/context_engine/router.py`
- **Why it is Tier C:** new API endpoints / response shape
- **Pilot changes include:** 147-line diff; likely adds explanation/familiarity endpoints
- **Recommendation:** review endpoints and contracts before merging.

### 7. `app/modules/timeline/router.py`
- **Why it is Tier C:** new or changed ADR-0008 endpoints
- **Pilot changes include:** 131-line diff
- **Recommendation:** review for page-manifest and ADR-0008 envelope interactions.

### 8. `app/modules/role_ui/router.py`
- **Why it is Tier C:** new or changed UI/SSOT flow
- **Pilot changes include:** 127-line diff
- **Recommendation:** review whether changes are SSOT-only or include response shape changes.

### 9. `app/services/emotion_engine.py`
- **Why it is Tier C:** new ADR-0008 surface (momentum / emotional checkpoints)
- **Pilot changes include:** 76-line diff
- **Recommendation:** review before merging.

### 10. `app/modules/fraud_exposure/service.py`
- **Why it is Tier C:** legal/privacy-sensitive (fraud exposure logic)
- **Pilot changes include:** 107-line diff
- **Recommendation:** review for legal/UPL risk before merging.

## Files to preserve from main (Tier A — no action)

The following files are present in `main` but largely removed/changed in `adr-0008-pilot` for cosmetic or non-functional reasons. Per the rulebook, keep main:

- `app/services/hud_funding_guide.py` (pilot removes; main-only service)
- `app/services/vault_engine.py` (pilot removes; main-only service)
- `app/services/progress_tracker.py` (pilot removes; main-only service)
- `app/services/court_form_generator.py` (pilot removes; main-only service)
- `app/services/proactive_tactics.py` (pilot removes; main-only service)
- `app/services/document_notarization.py` (pilot removes; main-only service)
- `app/services/event_extractor.py` (pilot removes; main-only service)
- `app/services/auto_mode_orchestrator.py` (pilot removes; main-only service)
- `app/modules/page_composer/router.py` (pilot removes; keep main)

## Files with purely Tier A diffs (keep main)

These files only have StrEnum → (str, Enum), emoji → symbol, `→` → `▸`, or `# noqa` / `usedforsecurity=False` removals. No functional change; keep main:

- `app/core/security_config.py`
- `app/modules/dev_lab/ideas.py`
- `app/modules/legal_trails/router.py`
- `app/core/id_gen.py`
- `app/services/vault_search.py`
- `app/core/event_bus.py`
- `app/core/context_envelope.py` (only adds unused `typing.Any` import)
- Many additional small router/service files with icon/arrow/StrEnum diffs

## Tier A no-op sweep result

A first-pass automated sweep of the remaining 267 changed `app/core/`, `app/modules/`, and `app/services/` files produced:

- **170 files classified as Tier A** (cosmetic: StrEnum, emoji → symbol, `→` → `▸`, `usedforsecurity=False`, `# noqa` removals, icon/log swaps, docstring/comment arrow swaps)
- **97 files classified as Tier C candidates** (new classes/functions, new endpoints, deleted-in-pilot files to preserve, or files in explicitly-deferred areas)
- **0 files classified as rulebook Tier B** (the easy patterns are exhausted)

The Tier C candidate list is a first cut; many candidates are likely cosmetic false positives, but they need human review because the diff also includes new `class`/`def` lines or endpoint decorations that could affect behavior.

## Status

- PR #60 (`phase-c-tier2-batch10`) **merged** — token manager async safety, ADR-0008 envelope files, async-token regression test.
- PR #61 (`phase-c-tier2-batch11`) **merged** — safe `app/main.py` Tier B fixes (token/utc/SSOT/escape-hatch).
- PR #62 (`phase-c-tier2-batch12`) **merged** — `app/modules/eviction_timeline/router.py` SSOT redirect fix.
- PR #65 (`phase-c-tier2-batch13`) **merged** — ADR-0008 pilot wiring for Context Engine, Eviction Timeline `/envelope` + `/momentum-checkpoint`, Vault `/envelope`, Timeline, Role UI, Storage, Emotion Engine, and the end-to-end `test_information_orchestrator_pilot.py` suite. `github-direct/main` HEAD: `7c5b5733`.
- Remaining `adr-0008-pilot` work: `app/main.py` page-manifest changes (`todo-065`), `app/modules/page_composer/assembly.py`, `app/core/page_manifest.py`, and `app/modules/fraud_exposure/service.py` still under review.

## Repo cleanup items

- The `origin` remote in this worktree points to the local path `C:/master-repo/sources/app-semptify-fastapi` instead of GitHub. This causes a false "ahead by 66 commits" reading against `github-direct/main`. Remove or repoint the `origin` alias to `https://github.com/1semptify-arch/Semptify.git` when convenient.
