# Handoff — Reconciling `adr-0008-pilot` with `origin/main`

**Status:** Not started. This is a fresh, scoped task — read in full before touching anything.
**Nothing has been lost.** No force-pushes have happened. A full backup exists: `backup/adr-0008-pilot-full-history` (pushed to GitHub, matches `adr-0008-pilot` exactly as of 2026-08-10).
**Do not treat this as urgent.** This should be done carefully, in a fresh session, not squeezed in at the end of a long one. Rushing this is the single biggest risk to the whole project.

---

## 1. How this situation happened (context, not blame)

Two lines of work grew independently for weeks:

- **`adr-0008-pilot`** — a local branch that accumulated 76 commits of real, working, mostly-tested changes: the full codebase audit (`todo-045`–`todo-062`), GUI page template batches, the ADR docs (0001–0007), the recurring scheduler/staleness-check tooling, a passing Playwright suite, and — most recently — the ADR-0008 Information Orchestrator pilot (`todo-063`–`075`).
- **`origin/main`** — moved independently via a normal PR workflow (PRs #28–#32), plus a scheduled GitHub Action ("Module Registry Verification") that commits routine sync updates on a timer. Confirmed: this movement was you, via your own account, via normal merges — not a rogue process.

Neither side is "wrong." Both contain real work the other doesn't have. This is a genuine two-way reconciliation, not a simple "push branch to main."

---

## 2. Current known inventory (from investigation, 2026-08-10)

**Overlap:**
| Bucket | Count | Meaning |
|---|---|---|
| Identical on both | 551 files | No action needed |
| Different content on both | 446 files | **Real conflicts — the hard part** |
| Only on `adr-0008-pilot` | ~1,590 files (bulk of the 1,638-file PR diff) | Needs to reach `main` |
| Only on `origin/main` | 42 files | Needs to be preserved, not overwritten |

**Notable content only on `main`** (do not lose these when reconciling): `app/services/vault_engine.py`, `app/services/court_form_generator.py`, `app/services/document_notarization.py`, `app/services/event_extractor.py`, `app/services/hud_funding_guide.py`, `app/services/proactive_tactics.py`, `app/services/progress_tracker.py`, docs: `ADMIN_MANUAL.md`, `AGENT_ORCHESTRATOR_MANUAL.md`, `CONTRACTS.md`, `CREDENTIALS_SETUP_WORKBOOK.md`, `DEPLOYMENT_GUIDE.md`, `MODULE_DEVELOPMENT.md`, `OAUTH_SETUP.md`.

**Notable content only on `adr-0008-pilot`** (do not lose these): the entire audit fix batch (`todo-045`–`062`), ADR docs 0001–0007 + `MOTIVATIONS.md` + `docs/doc-map.yaml` (commit `c4e7d9d5`), the codebase-wide quality audit (commit `ca711cb4`, 590 files different from main), all pilot ADR-0008 source (`context_envelope.py`, `page_envelope.py`, `experience_token.py`, eviction_timeline/vault envelope instrumentation, live narration wiring — see section 5 below for exact commits).

**The 446-file conflict zone includes core architecture files** — not edge cases: `app/core/navigation.py`, `app/core/oauth_token_manager.py`, `app/core/module_sdk.py`, `app/core/page_manifest.py`, `app/core/gdpr_compliance.py`, `app/core/gui_contract.py`, and roughly 440 more. Each of these needs an actual read-and-decide, not an automated resolution.

---

## 3. Recommended approach — category by category, not one big merge

Do not attempt a single rebase or merge across all 1,600+ files in one pass. Split by risk:

**Phase A — Zero-risk, do first:**
- The 551 identical files: no action, they'll match automatically in any merge tool.
- The ADR docs (commit `c4e7d9d5`) — 13 files, entirely new to `main`, no conflict possible. This should be its own tiny PR, mergeable same-day it's opened.

**Phase B — Low-risk, additive:**
- Files only on `adr-0008-pilot` that don't touch anything in the 446-conflict list (the bulk of GUI templates, most of the audit fixes, tooling scripts). These are additions, not conflicts — should merge cleanly.
- Preserve all 42 main-only files untouched throughout — nothing in this reconciliation should delete or overwrite them.

**Phase C — The real work: the 446-file conflict zone.**
- This needs to be worked through in logical groups, not alphabetically or all-at-once. Suggested grouping: (1) `app/core/` foundational files first, since everything else depends on these being right; (2) module-level router files; (3) test files last, since they should follow the source they test.
- For each file: read both versions in full before deciding. Prefer whichever version has the more complete/recent logic, but check whether the *other* side's version contains a fix the chosen version doesn't (e.g., if `main`'s `oauth_token_manager.py` has a fix that isn't in the pilot branch's version, that fix needs to be preserved even if the pilot branch's version is otherwise chosen as the base).
- One file (or small tightly-related group) per commit. Stop-and-report per standing rules — this is exactly the kind of work where scope creep turns a file-by-file review into a rushed bulk decision.

**Phase D — The pilot itself, last:**
- Once `main` and the reconciled branch agree on the 446 foundational files, the ADR-0008 pilot commits (see section 5) should apply cleanly on top, since they're new files with no main-side equivalent.

---

## 4. Hard constraints — do not violate these

- **No force-push without an explicit go-ahead per phase.** Each phase should be reviewed before the next one starts.
- **No bulk "take theirs" or "take mine" conflict resolution across many files at once.** Each of the 446 conflicting files gets an actual look, especially the `app/core/` ones.
- **Do not delete any of the 42 main-only files or their content**, even if a conflict resolution strategy would normally overwrite that path.
- **Do not touch `backup/adr-0008-pilot-full-history`.** It stays exactly as-is as the recovery point for the whole project until reconciliation is fully verified and merged.
- **Standing rules still apply throughout:** one task per commit, no self-approval, full-file preflight reads before edits, stop-and-report rather than scope-expand.

---

## 5. Reference — exact pilot commits (for Phase D)

| Deliverable | Commit | Files |
|---|---|---|
| Object Context Envelope | `d1e353ff` | `app/core/context_envelope.py` |
| Page Envelope | `db5fea0d` | `app/core/page_envelope.py` |
| Experience Token | `f6d85f84`, `e0496c08`, `f6bb48c6` | `app/core/experience_token.py` |
| Eviction Timeline instrumentation | `a54d4ced` | `app/modules/eviction_timeline/envelopes.py`, `router.py` |
| Vault upload instrumentation | `aebf178e` | `app/modules/vault/envelopes.py`, `router.py` |
| Live Event-Driven Narration | `26c51f61` | `app/services/vault_upload_service.py`, `app/services/document_flow_orchestrator.py`, `app/core/event_bus.py` |
| End-to-end pilot test | `ab1e5fdf` | `tests/test_information_orchestrator_pilot.py` |

Full reference doc: `ADR-0008-information-orchestrator.md` (Accepted, pilot-scoped to Eviction Timeline + Vault upload only).

---

## 6. Suggested first session prompt

```
Starting the adr-0008-pilot / main reconciliation project (see this
handoff doc in full first).

Begin with Phase A only:
1. Confirm backup/adr-0008-pilot-full-history still matches
   adr-0008-pilot exactly (sanity check, should be a no-op).
2. Create a new branch from current origin/main for the ADR docs:
   git checkout -b docs/adr-0001-0007 origin/main
   Cherry-pick just commit c4e7d9d5 onto it.
3. Push that branch and open a small, focused PR — just the 13 ADR/docs
   files, nothing else.
4. Stop and report. Do not proceed to Phase B without review.
```

Do not attempt Phase B, C, or D in the same session as Phase A without an explicit go-ahead — each phase should get its own clear-headed pass.

---

*This handoff is self-contained. A fresh Claude session or agent picking this up cold should not need anything else from today's conversation beyond this file and access to the repo.*
