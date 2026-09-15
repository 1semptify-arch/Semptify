---
mode: agent
description: Run preflight before every Agent Orchestrator task dispatch
---

<!-- Mirrors .devin/skills/orchestrator_preflight/SKILL.md — keep both in sync when editing. -->

# Agent Orchestrator — Pre-task Pre-Flight

Run this immediately before dispatching **any** task. One task, one preflight.

## Step 0: Freshness & canonicity gate

Before dispatching any task, run the freshness & canonicity check from `.devin/skills/preflight/SKILL.md` Steps 1a–1c (mirrored in `.github/prompts/preflight.prompt.md`) against the task's own description and `file_path`. Task descriptions in `orchestrator_state.json` / `agent_orchestrator_tasks.json` are written by prior agent sessions and can themselves be stale — a task claiming a system is "resolved," "done," or pointing at a specific file is a claim to verify against live code, not a fact to dispatch on. If the task touches a known-duplicated area (template-N/`themes/`/`design-system/`, the footer implementations, `context_loop`, or the feature-flag systems — see the table in Step 1a of the preflight skill) or any Know Your Rights Library / statute content, confirm canonicity/`review_status` before dispatch, or mark the task `blocked_on_decision` instead of dispatching on a best guess.

## Step 1: Read mandatory context

`REQUIRED_READING.md` is the canonical reading manifest — Tiers 1+2 are mandatory before dispatch. In order:

1. `AGENTS.md` — Python version, Known Failure Registry, swap protocol, module contracts.
2. `ACTIVE_CONTEXT.md` — what is being worked on right now.
3. `BUILD_STATE.md` — last 2 entries (what shipped, what is broken, what is pending).
4. `PROJECT_BIBLE.md` — canonical doc hierarchy and governance.
5. `CORE_CONTEXT.md` — Semptify purpose, banned language, no business-model terminology.
6. `SEMPTIFY_SYSTEM_MANIFEST.md` — module registry; required before touching any module or router.

## Step 2: Verify environment

- Python 3.11.9 is active (`venv311`).
- The app compiles:

```powershell
python -m py_compile app/main.py
```

## Step 3: Open the canonical state

The canonical orchestrator queue is `C:\master-repo\tools\orchestrator_state.json` (Postgres-backed via `tools/agent_ops_db.py`; never hand-edit it). Semptify's module-level queue `tools/agent_orchestrator_tasks.json` is a **mirror**, not a second source of truth — `python tools/sync_orchestrator.py` (full run) regenerates it from master and auto-promotes any local-only `pending`/`review`/`blocked_on_decision` task into master, and the pre-commit hook fails the commit if one is missed.

Read the master queue first. If a task genuinely exists only in the local mirror, run `sync_orchestrator.py` to promote it rather than working from the mirror.

## Step 4: Pick the next task

Filter by `status == open`, then highest `priority`.

- `model_tier: trusted` → SWE-1.7 / `swe-executor` work. Confirm `subagent_profile` is `swe-executor` and a `handoff_doc` exists.
- `model_tier: restricted` → GLM-5.2 / other restricted executor. Same claim path; the agent id must identify the restricted model (e.g. `glm-5.2`) — `orchestrator_mark_task.py` refuses restricted agents on `trusted` tasks.
- `model_tier: claude` → judgment work for the Claude orchestrator. Do not pick this unless you are the Claude parent.
- `model_tier: unassigned` → stop and let the orchestrator classify it first (`in_progress` is refused mechanically).
- `model_tier: unlimited` → retired tier (2026-09-11); it survives only on old closed records. If you find it on an open task, reclassify it (`trusted`/`restricted`/`claude`) before dispatch — do not dispatch it as-is.

For legacy Semptify tasks without `model_tier`, filter by `pending` and highest priority — but prefer promoting them to master first (Step 3).

## Step 5: Verify the file path

Before dispatching, confirm the file exists at the exact `file_path`. If not, flag it as a path error and stop.

## Step 6: Dispatch

### Master-level tasks (orchestrator_state.json)

For `model_tier: trusted`, the Claude orchestrator dispatches the `swe-executor` subagent using the handoff in `C:\master-repo\handoffs\<id>.md` (always via `.devin/skills/delegate_swe/SKILL.md` — it enforces the 2-concurrent cap). `restricted` tasks go to a restricted agent (GLM-5.2) through the same claim path. If you are the subagent:

1. Claim the task — `--preflight` is required and attests you ran the Step 0 freshness & canonicity gate against this task; the claim is refused without it:
   ```powershell
   python C:\master-repo\tools\orchestrator_mark_task.py <task_id> in_progress --agent swe-executor --preflight
   ```
2. Read the `handoff_doc`.
3. Execute the scope.
4. Run verification.
5. Write `C:\master-repo\handoffs\<task_id>-report.md`.
6. Mark the task `review` with usage:
   ```powershell
   python C:\master-repo\tools\orchestrator_mark_task.py <task_id> review --agent swe-executor --report-doc "C:\master-repo\handoffs\<task_id>-report.md" --usage '{"wall_clock_min": X, "tool_calls": Y}'
   ```
   If you hit a STOP AND REPORT trigger, mark `blocked_on_decision` instead:
   ```powershell
   python C:\master-repo\tools\orchestrator_mark_task.py <task_id> blocked_on_decision --agent swe-executor --blocked-reason "<why>"
   ```
7. Do NOT mark `resolved` or `rejected`. Stop and let the orchestrator decide.

### Legacy Semptify tasks (agent_orchestrator_tasks.json)

Prefer promoting the task to master first (Step 3) so it dispatches through the canonical path. If you genuinely must work from the mirror:

1. Update the task status to `in_progress` and set `assigned_agent` before writing any code:
   ```powershell
   python tools/mark_task_status.py <task_id> in_progress --agent <model-id>
   ```
2. Verify no other `in_progress` task already exists for the same `file_path`.
3. The Step 0 freshness & canonicity gate still applies — run it before editing even though the mirror can't enforce `--preflight` mechanically.

## Step 7: After the agent reports back

1. Review the diff. Verify changed files compile (`python -m py_compile <file>`).
2. For master-level tasks, the orchestrator updates the state to `resolved` (with `--pr`) or `blocked_on_decision`. Trusted/restricted executors stop at `review`.
3. For legacy Semptify tasks, update status:
   - `resolved` if the fix is merged and verified (privileged agents only).
   - `review` if it needs review first.
   - `blocked_on_decision` if a STOP AND REPORT trigger fires — it auto-surfaces to `decisions_pending_brad` once promoted to master.
   - `rejected` if it is not safe or not fixable (privileged agents only).
4. Update `BUILD_STATE.md` if the task resulted in shipped code.

## Step 8: Next task

Return to Step 1 for the next task.
