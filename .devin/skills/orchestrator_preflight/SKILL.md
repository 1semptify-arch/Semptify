---
name: orchestrator_preflight
description: Run preflight before every Agent Orchestrator task dispatch
---

# Agent Orchestrator — Pre-task Pre-Flight

Run this immediately before dispatching **any** task. One task, one preflight.

## Step 1: Read mandatory context

1. `AGENTS.md` — Python version, Known Failure Registry, swap protocol, module contracts.
2. `ACTIVE_CONTEXT.md` — what is being worked on right now.
3. `BUILD_STATE.md` — last 2 entries (what shipped, what is broken, what is pending).
4. `CORE_CONTEXT.md` — Semptify purpose, banned language, no business-model terminology.

## Step 2: Verify environment

- Python 3.11.9 is active (`venv311`).
- The app compiles:

```powershell
python -m py_compile app/main.py
```

## Step 3: Open the canonical state

The new master-level orchestrator queue is `E:\master-repo\tools\orchestrator_state.json`. Semptify's module-level queue `tools/agent_orchestrator_tasks.json` is still in use for Semptify-only tasks that have not been migrated.

Read `E:\master-repo\tools\orchestrator_state.json` first. If the task you are running is not there, fall back to `tools/agent_orchestrator_tasks.json`.

## Step 4: Pick the next task

Filter by `status == open`, then highest `priority`.

- `model_tier: unlimited` → SWE-1.7 / `swe-executor` work. Confirm `subagent_profile` is `swe-executor` and a `handoff_doc` exists.
- `model_tier: claude` → judgment work for the Claude orchestrator. Do not pick this unless you are the Claude parent.
- `model_tier: unassigned` → stop and let the orchestrator classify it first.

For legacy Semptify tasks without `model_tier`, filter by `pending` and highest priority.

## Step 5: Verify the file path

Before dispatching, confirm the file exists at the exact `file_path`. If not, flag it as a path error and stop.

## Step 6: Dispatch

### Master-level tasks (orchestrator_state.json)

For `model_tier: unlimited`, the Claude orchestrator dispatches the `swe-executor` subagent using the handoff in `E:\master-repo\handoffs\<id>.md`. If you are the subagent:

1. Claim the task:
   ```powershell
   python E:\master-repo\tools\orchestrator_mark_task.py <task_id> in_progress --agent swe-executor
   ```
2. Read the `handoff_doc`.
3. Execute the scope.
4. Run verification.
5. Write `E:\master-repo\handoffs\<task_id>-report.md`.
6. Mark the task `review` with usage:
   ```powershell
   python E:\master-repo\tools\orchestrator_mark_task.py <task_id> review --agent swe-executor --report-doc "E:\master-repo\handoffs\<task_id>-report.md" --usage '{"wall_clock_min": X, "tool_calls": Y}'
   ```
   If you hit a STOP AND REPORT trigger, mark `blocked_on_decision` instead:
   ```powershell
   python E:\master-repo\tools\orchestrator_mark_task.py <task_id> blocked_on_decision --agent swe-executor --blocked-reason "<why>"
   ```
7. Do NOT mark `resolved` or `rejected`. Stop and let the orchestrator decide.

### Legacy Semptify tasks (agent_orchestrator_tasks.json)

1. Update the task status to `in_progress` and set `assigned_agent` before writing any code:
   ```powershell
   python tools/mark_task_status.py <task_id> in_progress --agent <model-id>
   ```
2. Verify no other `in_progress` task already exists for the same `file_path`.

## Step 7: After the agent reports back

1. Review the diff. Verify changed files compile (`python -m py_compile <file>`).
2. For master-level tasks, the orchestrator updates the state to `resolved` (with `--pr`) or `blocked_on_decision`. Unlimited agents stop at `review`.
3. For legacy Semptify tasks, update status:
   - `resolved` if the fix is merged and verified.
   - `review` if it needs review first.
   - `rejected` if it is not safe or not fixable.
4. Update `BUILD_STATE.md` if the task resulted in shipped code.

## Step 8: Next task

Return to Step 1 for the next task.
