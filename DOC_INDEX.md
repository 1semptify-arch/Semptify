# DOC_INDEX.md — Source-of-Truth Doc Inventory

**Generated:** 2026-07-03
**Purpose:** Index of the 13 root-level docs that claim or imply canonical status. Each entry has a one-line description and a flag so a human (not the AI) can decide what to merge, archive, or delete.

## Flags:

- **KEEP AS-IS** — actively maintained or canonical per `PROJECT_BIBLE.md` hierarchy
- **STALE** — contradicts a newer file (named in the note)
- **DUPLICATE** — near-identical to another file (named in the note)

This index does NOT modify, merge, or delete any of the 13 files. It only describes them so a human can decide next steps.

---

## The 13 Files

| # | File | Description | Flag |
| --- | ------ | ------------- | ------ |
| 1 | `PROJECT_BIBLE.md` | Canonical governance: source-of-truth hierarchy (7 canonical docs), ethics, onboarding flow, doc-merge rules. Declares itself #1 in the hierarchy. | **KEEP AS-IS** — governance root, referenced by `AGENTS.md` and `ROADMAP_TO_PUBLIC_RELEASE.md` |
| 2 | `BLUEPRINT.md` | "Court Defense System Master Blueprint" — bi-directional data flow architecture, router/service/static inventory with statuses. Referenced a specific real court case (case number and party names removed 2026-09-05 — PII rule). | **STALE** — router/service statuses (many "Needs integration") contradict `ACTIVE_CONTEXT.md` which shows Phase 4 complete with full endpoint coverage for all 6 roles. **DUPLICATE** of `SEMPTIFY_SYSTEM_MANIFEST.md` (module inventory) |
| 3 | `BUILD_GUIDE_SSOT.md` | Build guide, testing checklist, known issues. Last updated May 20, 2026. Declares "Clean Repository - All Issues Resolved." | **STALE** — last updated May 20, 2026; contradicts `BUILD_STATE.md` (updated every session). **DUPLICATE** of `README.md` (which `PROJECT_BIBLE.md` declares as the canonical build guide) |
| 4 | `BUILD_STATE.md` | Live deployment state — what was shipped, what's known working, what's pending. Updated every session via `/ship` workflow. | **KEEP AS-IS** — actively maintained deploy log |
| 5 | `CORE_CONTEXT.md` | Mission/ethics foundation: "public utility not a product," Time to Real Help, who we build for, what we never build. Required reading per `/preflight` workflow. | **KEEP AS-IS** — mission foundation, referenced by `preflight.md` |
| 6 | `ACTIVE_CONTEXT.md` | Current priority, what's being worked on right now, anti-priorities, decision log. Last updated 2026-06-30. | **KEEP AS-IS** — actively maintained, single source of truth for current work |
| 7 | `SEMPTIFY_SYSTEM_MANIFEST.md` | Canonical module registry: active/disabled modules, product tiers, rules for adding modules. Last updated 2026-06-14. | **KEEP AS-IS** — canonical module registry, #7 in `PROJECT_BIBLE.md` hierarchy |
| 8 | `SEMPtIFY_CURRENT_MAP.md` | "Current State Map" — two competing systems (static HTML vs Jinja2), router status, 94 routers. Generated May 3, 2026. | **STALE** — generated May 3, 2026; describes "Onboarding/Reconnect Broken - In Repair" which `ACTIVE_CONTEXT.md` shows is fixed. **DUPLICATE** of `SEMPTIFY_SYSTEM_MANIFEST.md` (router inventory) |
| 9 | `ROADMAP_TO_PUBLIC_RELEASE.md` | Roadmap: completed phases, next-to-build list, anti-priorities, canonical docs list. Last updated 2026-06-29. | **STALE** — says "Phase 5b Action Feedback Helper 🎯 CURRENT PRIORITY" but `ACTIVE_CONTEXT.md` shows Phase 5b is ✅ COMPLETE (2026-06-30). **DUPLICATE** of `ACTIVE_CONTEXT.md` (next-to-build list, anti-priorities) |
| 10 | `STATUS_AUDIT.md` | Point-in-time module/function/contract engagement snapshot (2026-06-21): 95 active registrations, 49 contracts, 53 TODO markers, 60 pass-only functions, 148 HTML stubs. | **KEEP AS-IS** — historical snapshot, not meant to be updated. Referenced by `ACTIVE_CONTEXT.md` quick links |
| 11 | `STUB_AUDIT.md` | Point-in-time TODO/stub inventory (2026-06-19) across `app/`, `static/js/`, `app/templates/`. 5 priority tiers. | **STALE** — 3 of 5 Tier 1 items are now fixed: token refresh (Task 3, this session), `uploadToVault` (Task 1, commit `25e01d8`), timeline add-event (Task 2, this session). Still useful as historical reference but actively misleading if read as current |
| 12 | `ACTION_FEEDBACK_AUDIT.md` | Point-in-time audit (2026-06-21) of fetch calls, `alert()` usage, silent failures. 124 fetches, 82 alerts, ~76 silent failures. | **KEEP AS-IS** — historical snapshot. `ACTIVE_CONTEXT.md` shows Phase 5b (Action Feedback helper) is ✅ COMPLETE, but this doc was the design input, not the implementation status |
| 13 | `FNG_TODO.md` | "Fix Next, Grunt-work" list — bounded, non-urgent items. Design system reconciliation (3 parallel CSS systems), tenant home rebuild tasks. Last updated 2026-07-02. | **KEEP AS-IS** — actively maintained (updated 2026-07-02) |

---

## Summary

- **KEEP AS-IS:** 8 files (#1, #4, #5, #6, #7, #10, #12, #13)
- **STALE:** 5 files (#2, #3, #8, #9, #11)
- **DUPLICATE (also stale):** 4 of the 5 stale files overlap with a newer canonical file

## Recommended Human Decisions (not executed by AI)

1. **`BLUEPRINT.md` (#2)** — Archive or delete? Module inventory is superseded by `SEMPTIFY_SYSTEM_MANIFEST.md`. The bi-directional data flow architecture diagram may have historical value — if so, extract it before archiving.
2. **`BUILD_GUIDE_SSOT.md` (#3)** — Archive or delete? `README.md` is the canonical build guide per `PROJECT_BIBLE.md`. This file hasn't been updated since May 20, 2026.
3. **`SEMPtIFY_CURRENT_MAP.md` (#8)** — Archive or delete? Describes a broken state that's been fixed. Module inventory is superseded by `SEMPTIFY_SYSTEM_MANIFEST.md`.
4. **`ROADMAP_TO_PUBLIC_RELEASE.md` (#9)** — Merge into `ACTIVE_CONTEXT.md` or delete? The "completed phases" and "next to build" sections are duplicated in `ACTIVE_CONTEXT.md` which is more current.
5. **`STUB_AUDIT.md` (#11)** — Archive with a "SUPERSEDED" banner, or delete? 3 of 5 Tier 1 items are now fixed. The remaining items may still be valid but the file reads as current which is misleading.

---

*This index was produced by Task 6. The 13 original files were not modified or deleted.*
