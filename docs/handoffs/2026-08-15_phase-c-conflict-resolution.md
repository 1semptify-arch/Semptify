# Handoff — Phase C: Conflict Resolution (the 446-file zone)

**Part of:** `adr-0008-pilot` / `main` reconciliation. Read `HANDOFF_branch_reconciliation.md` first.
**Precondition:** Phase B is merged to `main`. Verify before starting.
**This is the hard, slow phase.** It will not finish in one session. Treat it as a multi-session project with a persistent tracker, not a single push-through task.

---

## 1. Why this phase is different from B and D

Every file here exists on both branches with genuinely different content. There is no mechanical "just take one side" answer — each file needs an actual read of both versions, because either side could contain a real fix, feature, or bugfix the other doesn't have. Rushing this is how real work quietly disappears.

## 2. Step 1 — Recompute and categorize the conflict list fresh

Same caution as Phase B: don't reuse the original 446-file count, re-derive it against current `main` (post Phase A + B):

```
git fetch origin main
git diff --name-status origin/main...adr-0008-pilot | grep '^M'
```

Then sort the resulting list into three priority tiers:

- **Tier 1 — Foundational `app/core/` files.** Everything else depends on these being right. Includes (from the original scan, re-verify current list): `navigation.py`, `oauth_token_manager.py`, `module_sdk.py`, `page_manifest.py`, `gdpr_compliance.py`, `gui_contract.py`, `event_subscribers.py`, `features.py`, `file_validator.py`, and others in that directory.
- **Tier 2 — Module-level router/service files.** Everything under `app/modules/*/` and `app/services/*` not already covered by Tier 1.
- **Tier 3 — Tests.** Should follow whatever the corresponding source file ends up looking like — resolve these last, and re-run them after Tier 1/2 decisions are made, not before.

## 3. Step 2 — Build a persistent tracker (required, not optional)

446 files cannot be tracked in your head across sessions. Generate a task-queue-style entry for each **batch** of ~15-25 related files (not one task per file — too granular; not one task for all 446 — too large to stop-and-report on meaningfully). Suggested batching: by subdirectory or by feature area within each tier.

Add these as entries in `agent_orchestrator_tasks.json` following your existing schema (id, title, description, category, target_model, priority, file_path, status, notes, created_at, updated_at, assigned_agent), starting at the next available `todo-` number. Example shape for one batch:

```json
{
  "id": "todo-0XX",
  "title": "Reconcile Tier 1 core files, batch 1 of N (navigation/auth)",
  "description": "Resolve conflicts between adr-0008-pilot and main for: app/core/navigation.py, app/core/oauth_token_manager.py, app/core/module_sdk.py [confirm exact list from Step 1]",
  "category": "refactor",
  "priority": "high",
  "file_path": "app/core/navigation.py; app/core/oauth_token_manager.py; app/core/module_sdk.py",
  "notes": "Preflight: read BOTH versions of each file in full before deciding. For each file, check whether the non-chosen side has a fix/feature the chosen side lacks — if so, merge that piece in manually rather than discarding it. Do not bulk-resolve. One commit per file or tightly-related pair. Stop and report per file group.",
  "status": "pending"
}
```

Generate the full batch list (this is itself worth a stop-and-report before starting resolution work) so there's a visible checklist of what's done vs. remaining across however many sessions this takes.

## 4. Step 3 — Resolve, one batch at a time

For each file in a batch:
1. Read the `main` version in full.
2. Read the `adr-0008-pilot` version in full.
3. Identify what each side has that the other doesn't — not just "which is newer," but genuinely diff the *logic*, since a smaller/older-looking change can still contain a real fix.
4. Write the reconciled version, preserving both sides' real content where they don't actually conflict in intent (e.g., one side added a bugfix, the other added a new function — both can survive).
5. Where they genuinely conflict in intent (two different approaches to the same problem), flag it for Brad rather than guessing — this is a judgment call, not a mechanical merge.

## 5. Guardrails

- No bulk "take theirs"/"take mine" across multiple files.
- No skipping the "read both in full" step, even for files that look like simple one-line differences — a one-line diff can still hide which line is the outdated one.
- Preserve all 42 main-only files throughout — don't let a batch operation accidentally touch them.
- One batch per commit/PR, not all 446 files in one PR.
- If a batch turns out to be bigger or messier than expected mid-work, stop and report rather than pushing through — re-scoping is fine, silent scope creep isn't.

## 6. Finishing a batch

- Push, open a PR per batch (or group a few related batches into one PR if small).
- Re-run relevant tests before requesting merge.
- Mark the corresponding `todo-0XX` task resolved in the tracker.
- **Stop between batches.** This phase is explicitly designed to span multiple sessions — there is no "finish Phase C in one sitting" expectation.

## 7. Moving to Phase D

Only once **all** Tier 1/2/3 batches are resolved and merged should Phase D begin — the pilot commits assume the core files are already settled.
