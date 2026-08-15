# HANDOFF: P4 Merge Sequence (PRs #74–#78) + P5 Kickoff

**Status:** P4 caller migrations complete, 5 PRs open, not yet merged. Two issues must be resolved before merging, not after.

---

## 1. Two things to resolve first

**Collision risk — #74 and #76 both touch `app/services/auto_mode_orchestrator.py`.**
#74 migrates/likely deletes this file. #76 lists it as a modified file (pointing its `proactive_tactics` import at the new location). If #74 deletes it and #76 edits it, second-to-merge either conflicts or resurrects a deleted file. Check before merging either:

```
gh pr diff 74 --repo 1semptify-arch/Semptify -- app/services/auto_mode_orchestrator.py
gh pr diff 76 --repo 1semptify-arch/Semptify -- app/services/auto_mode_orchestrator.py
```

If #74 deletes the file, merge #74 first, then rebase #76 on new main and resolve that hunk (drop the edit if the file's gone, or redirect it to the file's new location).

**`phase2-dc4e66-065` is only half done — don't let it get marked resolved.**
Caller migration to `app/modules/dashboard/service.py` is complete (PR #77), but the "review dashboard/progress wiring" portion was explicitly not covered. Before or alongside merging #77:

```
python tools/mark_task_status.py phase2-dc4e66-065 --agent devin --notes "Caller migration to app/modules/dashboard/service.py complete (PR #77). Dashboard/progress wiring review NOT done — tracked separately."
```

Then open a fresh task for the wiring review — don't close dc4e66-065 as if the whole thing landed.

---

## 2. Merge sequence — run `sync_orchestrator.py --check` after every single merge

```
# 1. auto_mode_orchestrator — resolve first, it's the file the collision centers on
gh pr diff 74 --repo 1semptify-arch/Semptify -- app/services/auto_mode_orchestrator.py
gh pr merge 74 --repo 1semptify-arch/Semptify --merge
git checkout main && git pull github-direct main
python tools/sync_orchestrator.py --check

# 2. proactive_tactics — rebase against new main first, resolve the collision file
git checkout devin/p4-proactive-tactics   # confirm actual branch name for PR #76
git merge main
# resolve any conflict/stale edit on auto_mode_orchestrator.py here
git push github-direct HEAD
gh pr merge 76 --repo 1semptify-arch/Semptify --merge
git checkout main && git pull github-direct main
python tools/sync_orchestrator.py --check

# 3. event_extractor — no known collision
gh pr merge 75 --repo 1semptify-arch/Semptify --merge
git checkout main && git pull github-direct main
python tools/sync_orchestrator.py --check

# 4. progress_tracker — split dc4e66-065 status first (section 1), then merge
python tools/mark_task_status.py phase2-dc4e66-065 --agent devin --notes "Caller migration to app/modules/dashboard/service.py complete (PR #77). Dashboard/progress wiring review NOT done — tracked separately."
gh pr merge 77 --repo 1semptify-arch/Semptify --merge
git checkout main && git pull github-direct main
python tools/sync_orchestrator.py --check

# 5. state docs — last, should reflect the final settled state of 1–4
gh pr merge 78 --repo 1semptify-arch/Semptify --merge
git checkout main && git pull github-direct main
python tools/sync_orchestrator.py --check
```

If `--check` ever fails or the task/path counts shift unexpectedly at any step, stop there and report — don't continue merging into an unverified main.

---

## 3. After all five are clean

Confirm final state:

```
python tools/sync_orchestrator.py --check
python -c "
import json
data = json.load(open('tools/agent_orchestrator_tasks.json'))
from collections import Counter
print(Counter(t['status'] for t in data))
"
```

Then proceed to **P5 — Tier C ADR-0008 wiring module clusters** (~20 tasks: `page_composer`, `context_engine`, `eviction_timeline`, `vault`, `page_shell`, `documents`, `intake`, `tactics`, `progress`, `onboarding`, `public_exposure`, etc.). These are mostly independent module clusters and can likely run in parallel across agents now that the P4 collision is resolved — no need to serialize them the way P4 required.

Dispatch prompt for P5:

```
Proceed to P5: Tier C ADR-0008 wiring module clusters (~20 tasks) from tools/phase_c_tier2_reconciliation_tasks.json.
One task per module cluster, one PR per task where practical. Confirm main is clean (sync_orchestrator.py --check) before branching for each. Flag any cross-cluster file overlaps before merging (per the #74/#76 lesson from P4) rather than discovering them mid-merge.
```
