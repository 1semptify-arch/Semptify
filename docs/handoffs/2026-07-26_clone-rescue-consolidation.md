# Handoff — Clone Rescue & Consolidation

**Status:** Rescue pushes requested but not yet confirmed. Do not proceed past Step 1 until confirmed done.
**Blocks:** All of Phase B/C/D (`HANDOFF_branch_reconciliation.md` and its phase docs). Do not resume that project until this handoff is fully complete.
**Do not run `/ship` from anywhere until Step 4 below is done.**

---

## 1. What happened (context)

An investigation into why `origin/main` kept moving unexpectedly during the ADR-0008 pilot reconciliation (see `HANDOFF_branch_reconciliation.md`) surfaced something bigger: the project exists as multiple independent local git clones across drives, each capable of pushing to GitHub independently without the others knowing. Full inventory:

| Clone path | Type | Remote | Branch | Status |
|---|---|---|---|---|
| `C:\master-repo\sources\app-semptify-fastapi` | Real clone | `github.com/1semptify-arch/Semptify.git` | `docs/adr-0001-0007` | 11 uncommitted files (untracked), 1 unpushed commit on `walnut-gauss` |
| `C:\master-repo\modules\app-semptify-fastapi` | Git submodule of `sources/` (working as designed) | Local path to `sources/` | `adr-0008-pilot` | 1 uncommitted file, **40 unpushed-only commits across 2 branches** |
| `C:\Users\bradc\Downloads\Semptify-Archive-20260409-012245\...` | Old archive clone | GitHub | `main` | Clean, inert, nothing unique |
| `C:\Users\bradc\Downloads\WindowsAppSDK\Semptify-Archive-20260409-012245\...` | Old archive clone (duplicate of above) | GitHub | `main` | Clean, inert, nothing unique |
| `C:\Users\bradc\.windsurf\worktrees\...\walnut-gauss` | **Broken** — no `.git` metadata | N/A | N/A | Full file tree from 7/26/2026 present on disk, but no git history attached |
| `C:\Semptify\Semptify-FastAPI` | **Not a git repo at all** | N/A | N/A | This is what the `/ship` script has been targeting — it's been pushing to a dead folder |

**The real risk:** 40+ commits exist on exactly one hard drive, on nowhere else, not on GitHub, not on any backup.

## 2. The three at-risk commit sets (need rescue, not yet decisions)

1. **`backup/local-main-pre-reset`** — 33 commits, only in `modules/`, doesn't exist anywhere else including `sources/` or GitHub.
2. **`local/markdown-lint-pass`** — 7 commits in `modules/`, and a *different* branch of the same name exists in `sources/` (different commit history — `275151a6` vs `0f8beb5e`). These are two different things that happen to share a name.
3. **`walnut-gauss`** — 1 unpushed commit in `sources/`, roughly 2 weeks old (2026-07-26).

## 3. Step 1 — Rescue pushes (do this first, before anything else in this doc)

```
cd C:\master-repo\modules\app-semptify-fastapi
git remote add github-direct https://github.com/1semptify-arch/Semptify.git
git push github-direct backup/local-main-pre-reset:backup/RESCUE-modules-local-main-pre-reset
git push github-direct local/markdown-lint-pass:backup/RESCUE-modules-markdown-lint-pass

cd C:\master-repo\sources\app-semptify-fastapi
git push origin walnut-gauss:backup/RESCUE-sources-walnut-gauss
```

**Confirm all three succeeded** — check the branches actually exist on GitHub before proceeding. If you're picking this up and don't know whether this already happened, check GitHub for branches named `backup/RESCUE-*` before re-running these commands.

## 4. Step 2 — Investigate the orphaned Windsurf worktree (after Step 1 confirmed)

`C:\Users\bradc\.windsurf\worktrees\Semptify-FastAPI\Semptify-FastAPI-walnut-gauss` has real files from 7/26/2026 but no working `.git` metadata (`.git` file points to a path that no longer exists). Two possibilities:

- It's just a stale copy of the same `walnut-gauss` commit already rescued in Step 1 — in which case, nothing further needed, safe to delete.
- It contains edits made *after* that commit that were never saved anywhere — in which case those edits need to be diffed against the rescued `walnut-gauss` commit and manually recovered if they're real and different.

```
Compare the file contents of C:\Users\bradc\.windsurf\worktrees\Semptify-FastAPI\Semptify-FastAPI-walnut-gauss
against the commit now at backup/RESCUE-sources-walnut-gauss. Report
whether they're identical or whether the worktree has newer/different
content. Do not delete the worktree folder until this is confirmed either
way.
```

## 5. Step 3 — Decide what to do with the 40+ rescued commits

Once safely on GitHub, these don't need to be resolved immediately — they need to be **understood** before deciding whether they merge into the reconciliation project (as more Phase C-style work) or get archived as superseded/abandoned experiments. Do not assume they're all still wanted; some may be exactly what their names suggest (a pre-reset backup that was intentionally reset away from). This decision is Brad's to make after seeing what's actually in them, not something to auto-merge.

## 6. Step 4 — Fix `/ship` and consolidate to one canonical clone

- `C:\Semptify\Semptify-FastAPI` is not a git repo — the `/ship` script's `cwd` has been pointing at a dead folder. **Update `/ship` to target `C:\master-repo\sources\app-semptify-fastapi`** — that's the one real, GitHub-connected clone, and the natural canonical choice.
- `C:\master-repo\modules\app-semptify-fastapi` is a legitimate git submodule of `sources/` — this is working as originally designed, not a problem to fix. Leave it as-is.
- The two `Downloads\...\Semptify-Archive-...` folders are old and inert — safe to delete or ignore, nothing unique in them.
- Once `/ship` is repointed, verify one clean run of it against `sources/` before trusting it again.

## 7. Only after Steps 1–4 are done: resume the reconciliation project

Return to `HANDOFF_branch_reconciliation.md` and its Phase B/C/D docs. Before resuming Phase B specifically, re-verify: does the reconciliation's "446 conflict files" analysis still hold, or does it need to account for anything found in the rescued commits from Step 3? If the rescued commits touch any of the same core files already flagged in Phase C, that's worth knowing before Phase C batches get built.

---

*This handoff is self-contained. Start at Step 1, verify each step before moving to the next, and don't let urgency compress the "confirm before proceeding" checks — that's exactly the instinct that created this situation in the first place.*
