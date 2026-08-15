# Handoff — Clone Rescue & Consolidation (Status Update)

**Supersedes:** `HANDOFF_clone_rescue_consolidation.md` (Steps 1–2 now complete, this file reflects current state)
**Still blocks:** All of Phase B/C/D branch reconciliation (`HANDOFF_branch_reconciliation.md`). Do not resume that project until Step 4 below is done.
**Do not run `/ship` from anywhere until Step 4 is done.**

---

## 1. Completed so far

**Step 1 — Rescue pushes: DONE, confirmed on GitHub.**
| Branch | Rescued to | Commit |
|---|---|---|
| `backup/local-main-pre-reset` | `backup/RESCUE-modules-local-main-pre-reset` | `c194ab6b` |
| `local/markdown-lint-pass` | `backup/RESCUE-modules-markdown-lint-pass` | `0f8beb5e` |
| `walnut-gauss` | `backup/RESCUE-sources-walnut-gauss` | `a8c6423a` |

**Step 2 — Orphaned Windsurf worktree: DONE, resolved and deleted.**
Compared against `backup/RESCUE-sources-walnut-gauss` under the correct pinned interpreter (`venv311`, not system Python 3.14 — that distinction mattered, see note below). Result: 1,840/1,840 files identical, zero differences. Confirmed as a stale duplicate, not unique content. Deleted via `Remove-Item -Recurse -Force`.

**Note on tooling:** the first comparison attempt ran under system Python 3.14 instead of the project's pinned 3.11.9, which risked an inaccurate result (3.14 changed `tarfile.extractall()` behavior). Re-ran under `venv311\Scripts\python.exe` for a trustworthy result. **Any future script involving file extraction/comparison on this project should explicitly use the venv311 interpreter, not a bare `python` call** — this is a recurring risk, not a one-off.

---

## 2. Step 3 — Investigating the two rescued commit sets (in progress)

### `backup/RESCUE-modules-markdown-lint-pass` — mostly resolved
- The 2 headline commits (`8013e644` bulk markdown lint, `0f8beb5e` cleanup) are confirmed already on `main` via PR #17 (`d22c85a4`/`275151a6`, matching content under different hashes).
- **Still open:** 5 other commits on this same branch were never checked against `main`: `f59ad8eb` (.devin/workflows → .devin/skills migration), `4d307317` (--status flag fix), `009fd39e`/`75720093`/`0802902e` (path-reference updates to E:\master-repo paths).

```
Check whether these 5 commits from backup/RESCUE-modules-markdown-lint-pass
are also already present on current origin/main in some form (three-bucket
comparison, same method as before): f59ad8eb, 4d307317, 009fd39e, 75720093,
0802902e

If all confirmed present, this branch is fully closed — archival record
only, no further action.
```

### `backup/RESCUE-modules-local-main-pre-reset` — origin clarified, comparison still pending
- **Confirmed by Brad: this was never a human action.** No manual backup, no manual reset. Both the original 33-commit scaffold work (`eviction_timeline`, `dispute_tracker`, admin hub tiles, GUI ordering rules — dated 2026-07-29) and the later `git reset --hard origin/main` that discarded it were autonomous AI actions (Copilot), not something Brad did or was aware of.
- **This is a real gap worth a standing rule** (flagged for later, not blocking right now): no `git reset --hard` on `main` should happen without explicit human confirmation, the same way no-self-approval already governs merges. Revisit once the immediate rescue work is done.
- **Not yet run:** the comparison to determine whether current `main`'s `eviction_timeline`/`dispute_tracker` evolved from this backup or is a separate rebuild.

```
Compare the eviction_timeline and dispute_tracker modules as they exist
on current origin/main against how they looked in
backup/RESCUE-modules-local-main-pre-reset at commits c069fae1
(eviction_timeline scaffold) and 0eedcc36 (dispute_tracker scaffold).

Specifically:
1. Do the current main versions share meaningful code/structure with the
   backed-up versions (same field names, same approach, evolved from
   this), or are they structurally unrelated (different data models,
   different approach entirely)?
2. Does current main's eviction_timeline have the FunctionGroupContract
   guardrails, admin hub tile wiring, and footer/help page changes that
   this backup branch added, or are those specifically missing from main?

Report back which scenario it looks like: (A) main's version evolved
from this backup, safe to leave archived, or (B) main's version is an
unrelated rebuild and this backup may contain features/approaches that
never made it anywhere.
```

**Why this specifically matters for the reconciliation project:** `eviction_timeline` is one of the two ADR-0008 pilot surfaces (`todo-073`). If scenario (B) is true, there may be design decisions or approaches in this backup worth a look before finalizing Phase C/D work on that module — not necessarily code to reuse, but context worth having.

---

## 3. Step 4 — Not started yet: fix `/ship`, consolidate to one clone

Once Step 3's two open items above are resolved:

- Repoint the `/ship` skill's working directory from the dead `C:\Semptify\Semptify-FastAPI` (confirmed not a git repo at all) to `E:\master-repo\sources\app-semptify-fastapi` — the one real, GitHub-connected clone.
- `E:\master-repo\modules\app-semptify-fastapi` is a legitimate git submodule of `sources/` — working as designed, no change needed.
- The two `Downloads\...\Semptify-Archive-...` folders are old, inert, nothing unique — safe to delete or ignore.
- Verify one clean `/ship` run against the corrected path before trusting it again.

---

## 4. After Step 4: resume the reconciliation project

Return to `HANDOFF_branch_reconciliation.md` and Phase B. Before resuming, re-check whether anything found in Step 3 (especially the `eviction_timeline`/`dispute_tracker` comparison) changes what Phase C's conflict-file list should include.

---

*This handoff is self-contained. A fresh session should start by running the two Step 3 investigation blocks above (order doesn't matter between them, both are independent), then proceed to Step 4 once both report back.*
