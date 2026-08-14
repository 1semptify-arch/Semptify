# Phase C Tier 2 — Continue Handoff

**Milestone:** ADR-0008 pilot wiring has landed on `main`.

**Merge commit:** `7c5b5733`  
**Merged PR:** #65 (`phase-c-tier2-batch13`)  
**Date:** 2026-08-14

## What just shipped

PR #65 merged the functional ADR-0008 pilot pieces from `adr-0008-pilot` into `main`:

- `app/modules/context_engine/router.py` — Layer 1 explanation CRUD and Layer 2 metadata retrieval endpoints.
- `app/modules/eviction_timeline/router.py` — new `/envelope` and `/momentum-checkpoint` endpoints.
- `app/modules/eviction_timeline/register.py` — contract registration for the two new routes.
- `app/modules/vault/router.py` — new `/envelope` endpoint for vault documents.
- `app/modules/role_ui/router.py`, `app/modules/storage/router.py`, `app/modules/timeline/router.py` — reconciled ADR-0008 wiring and safer main defaults.
- `app/services/emotion_engine.py` — warm, intensity-scaled momentum checkpoints.
- `tests/test_information_orchestrator_pilot.py` — end-to-end pilot suite (12 tests, all passing in CI).
- Supporting tracker/tools updates (`BUILD_STATE.md`, `tools/*`).

The full pilot suite passed both locally and in CI before merge.

## Status table

| Batch | PR | Status | Notes |
|---|---|---|---|
| 10 | #60 | merged | Token manager async safety, ADR-0008 envelope files, async-token regression test. |
| 11 | #61 | merged | Safe `app/main.py` Tier B fixes (token/utc/SSOT/escape-hatch). |
| 12 | #62 | merged | `app/modules/eviction_timeline/router.py` SSOT redirect fix. |
| 13 | #65 | **merged** | **ADR-0008 pilot wiring + end-to-end test on `main`.** |
| 14+ | — | open / pending | Remaining Tier C work (see below). |

## Remaining Tier C work (do not continue without explicit authorization)

- `app/main.py` — page-manifest / template-assembly changes (`todo-065`).
- `app/core/page_manifest.py` — 410-line page-manifest / template migration (`todo-065`).
- `app/modules/page_composer/assembly.py` — page assembly and template rendering diffs (`todo-065` scope review).
- `app/modules/fraud_exposure/service.py` — legal/privacy-sensitive fraud exposure logic.

## ADR-0008 status

`docs/adr/0008-information-orchestrator.md` has been updated to reflect that the pilot surfaces (Eviction Timeline and Vault upload flow) are now on `main`. Full-platform rollout beyond the two pilot surfaces remains a separate future decision.

## Next actions

1. Continue `todo-065` page-manifest / template-assembly pass only after user authorization.
2. Review `app/modules/fraud_exposure/service.py` for legal/UPL risk before any pilot changes are applied.
3. Keep reconciliation batches at 8–10 files and run the full test suite per PR.

---

*Do not self-merge further PRs without explicit user authorization.*
