# HANDOFF: Post-PR #69 — Verify, Prioritize, Dispatch

**Status:** PR #69 open, not yet confirmed merged. This doc covers everything from here through releasing the 38 Tier 2 tasks to the agent fleet.

---

## 1. Where things stand

- **PR #69** — `tools/tier2-reconciliation-sync` → `main`. Tracker/JSON/HTML only, no app code. Commit `1f4e7847`.
  - https://github.com/1semptify-arch/Semptify/pull/69
- Contains 38 new Tier 2 reconciliation tasks (see `HANDOFF_tier2_adr0008_reconciliation.md` for full methodology/reasoning behind the buckets).
- Tracker total: 89 tasks — 50 resolved, 38 pending, 1 review.
- Scratch diff files archived at `tools/recon/tier2_179_diff.txt` and `tools/recon/tier2_core_78_diff.txt`.

---

## 2. First: verify the merge, don't assume it

```
gh pr view 69 --repo 1semptify-arch/Semptify --json state,mergeable,statusCheckRollup
```

- If CI is green and mergeable → merge it.
- If the Test job hangs (same symptom as PR #59) → note it. Two PRs hanging on the same job is a signal the problem is environmental/infra, not code-specific to either PR. Don't debug it as if it's this PR's fault — flag it as a separate investigation.

Once merged:

```
git checkout main
git pull github-direct main
python tools/sync_orchestrator.py --check
```

Confirm it still reports `89 task(s)` with `0 missing paths` on main directly (not just the branch) before dispatching anything.

---

## 3. Before dispatching — one integrity check

During the merge, `sync_orchestrator.py` auto-generated tasks `phase2-ee178d-068` through `phase2-980e19-075` (vault_engine, vault_installer, tactics, timeline, core security/auth diffs, core cosmetic preserve). These appeared in the commit log alongside the 38 manually-bucketed tasks.

**Confirm these are the doc-sourced expansion of the same 38 (i.e., part of the count), not duplicates layered on top.** Quick check:

```
python -c "
import json
data = json.load(open('tools/agent_orchestrator_tasks.json'))
ids = [t['id'] for t in data if t['id'].startswith('phase2-')]
print(len(ids), 'phase2 tasks')
print(sorted(ids))
"
```

If the count matches expectations (38 pending + already-resolved ones from this batch) and there's no duplicate coverage of the same file paths, proceed. If something looks doubled, stop and report back before dispatching — don't let agents pull duplicate work.

---

## 4. Dispatch order (priority, not alphabetical)

Do **not** let agents pull from the queue in default/alphabetical order. Hand-sequence it:

### Priority 1 — Security review (dispatch first, independent of queue order)
- **`services/document_flow_orchestrator.py`** — f-string SQL injection regression in pilot branch.
- Main's parameterized-query version is the permanent baseline. Pilot's version **does not land** under any circumstance without a separate, explicit fix-and-review cycle.
- Assign to whichever agent is free next — don't wait for it to come up in normal rotation.

### Priority 2 — Low-risk deletions (quick wins, build momentum)
- `court_form_generator.py` — delete after compile/test check
- `hud_funding_guide.py` — delete after compile/test check

### Priority 3 — Deletions needing test migration first
- `vault_engine.py` — migrate `tests/` imports, then delete
- `document_notarization.py` — migrate `tests/` imports, then delete

### Priority 4 — Caller migrations (highest complexity, do after 1–3 build confidence)
- `auto_mode_orchestrator.py` — migrate callers to `app/modules/auto_mode/service.py`, then delete
- `event_extractor.py` — migrate callers to `app/modules/documents/service.py`, then delete
- `proactive_tactics.py` — migrate callers to `app/modules/tactics/service.py`, then delete
- `progress_tracker.py` — migrate callers to `app/modules/dashboard/service.py`, then delete

### Priority 5 — Tier C ADR-0008 wiring (~20 tasks)
- `page_composer/`, `context_engine/`, `eviction_timeline/`, `vault/`, `page_shell/`, `documents/`, `intake/`, `tactics/`, `progress/`, `onboarding/`, `public_exposure/`, etc.
- These can run in parallel across agents once Priority 1–4 are clear, since they're mostly independent module clusters.

### Priority 6 — Tier C legal/money/privacy/storage catch-alls (4 tasks)
- Eviction services, funding, legal-money-privacy, security/vault/storage.
- Lower urgency; these are broader sweeps rather than pinpointed migrations.

### Deferred — do not dispatch
- **Tier B cosmetic preserve** (5 tasks) — blanket "preserve main" rule applies, **except** any file touching SQL/auth/permissions/security logic, which gets pulled for manual review regardless of diff size. Two of five already resolved (contacts+hud_funding, services/recognition/); remaining three pending spot-check confirmation, not urgent.
- **`app/core/page_manifest.py`** — stays under existing `todo-065`, not part of this batch. Do not duplicate.

---

## 5. Standing rules that still apply (don't relax these under dispatch pressure)

- No `git reset --hard` on any branch without explicit human confirmation.
- One task per commit. No self-approval. Preflight full-file reads before edits.
- Stop-and-report rather than scope-expand — if an agent finds a caller migration is bigger than expected, it reports back rather than quietly widening the task.
- Tier A decisions (already made above) are final for this batch — agents should execute, not re-litigate deletion buckets.
- Commit messages must use the `admin:` / `user:` / `help:` / `adr:` prefix (pre-commit hook enforces this — don't bypass with `--no-verify`).

---

## 6. What Brad still needs to decide (nothing blocking right now)

- Sequencing of `local/markdown-lint-pass` (278 files, still unpushed, separate PR) relative to this batch — recommend pushing it once PR #69/security task are clear, not before, so CI signal stays easy to read.
- Whether to open a separate investigation into the Test-job-hang pattern if it recurs on PR #69 (seen once already on PR #59).
