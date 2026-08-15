# Handoff — Phase B: Additive Merge

**Part of:** `adr-0008-pilot` / `main` reconciliation. Read `HANDOFF_branch_reconciliation.md` first for full context if you haven't already.
**Precondition:** PR #34 (Phase A — ADR docs) is merged to `main`. Verify this before starting — if it isn't merged yet, stop and merge it first.
**Do not start this in the same session Phase A was merged in.** Fresh session, fresh attention.

---

## 1. What this phase does

Merges everything on `adr-0008-pilot` that is **purely additive** — files that don't exist on `main` at all, and don't touch anything in the known 446-file conflict zone (that's Phase C's job, not this one). This should be a clean, low-drama merge if scoped correctly. If it isn't clean, that's a signal the file list needs re-checking, not a signal to force through conflicts here.

## 2. Step 1 — Recompute the file list fresh (do not reuse old numbers)

The original investigation's counts (1,638 total diff, 446 conflicting, 42 main-only) were measured *before* Phase A merged. Re-run the three-bucket comparison now, against current `origin/main`:

```
git fetch origin main
git diff --name-status origin/main...adr-0008-pilot
```

Then classify every file into exactly one bucket:
- **Identical** — skip, no action needed
- **New on `adr-0008-pilot`, doesn't exist on `main`** — this phase's target
- **Exists on both, different content** — Phase C's job, exclude from this phase entirely
- **Only on `main`** — do not touch, must be preserved

Report the fresh counts before proceeding. They should be close to the original numbers minus the 13 ADR files (already merged in Phase A) but confirm rather than assume.

## 3. Step 2 — Build the merge

```
git checkout -b reconciliation/phase-b origin/main
```

Apply only the "new, no conflict" files from `adr-0008-pilot` onto this branch. Cherry-picking the original commits directly will likely pull in conflicting files too (many commits touch a mix of new and conflicting files) — so this probably needs to be done as a **file-level apply**, not a commit-level cherry-pick:

```
git checkout adr-0008-pilot -- <path-to-new-file-1> <path-to-new-file-2> ...
```

Do this in logical batches (e.g., by directory: all of `docs/`, then all of `tools/`, then all of `app/modules/*/` that are new modules, etc.), committing each batch separately. This keeps history readable and keeps any single commit small enough to review.

## 4. Guardrails

- **If a file you're about to add turns out to already exist on `main`** (meaning the fresh diff in Step 1 was stale or miscounted), stop adding it — that file belongs in Phase C, not here.
- **Do not touch any of the 42 main-only files.**
- **Do not resolve any conflicts in this phase.** If `git checkout adr-0008-pilot -- <path>` would overwrite something different on `main`, that path shouldn't have been in this phase's list — pull it out, flag it for Phase C.
- One batch per commit, stop-and-report per standing rules.

## 5. Finishing

- Push `reconciliation/phase-b`, open a PR into `main`.
- PR description should state the file count and confirm zero files from the known conflict zone were touched.
- Get sign-off before merging — this PR will likely be large (file count), so a careful skim of the file list (not every line of every file) is reasonable before approving.
- **After merge: stop.** Do not start Phase C in the same session.
