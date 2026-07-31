---
description: Run preflight before every Agent Orchestrator task dispatch
---

# Agent Orchestrator — Pre-task Pre-Flight

Run this immediately before dispatching **any** task from the orchestrator queue. One task, one preflight.

## Step 1: Read mandatory context

Read these files before selecting a task:

1. `AGENTS.md` — Python version, Known Failure Registry, swap protocol, module contracts.
2. `ACTIVE_CONTEXT.md` — what is being worked on right now.
3. `BUILD_STATE.md` — last 2 entries (what shipped, what is broken, what is pending).
4. `CORE_CONTEXT.md` — Semptify purpose, banned language, no business-model terminology.

## Step 2: Verify environment

- Python 3.11.9 is active (`venv311`).
- The app compiles:

```powershell
cd E:\master-repo\sources\app-semptify-fastapi
python -m py_compile app/main.py
```

## Step 3: Open the orchestrator

Two UIs, same queue data:

- **Standalone UI** (works offline or served by FastAPI):
  - `file:///E:/master-repo/sources/app-semptify-fastapi/tools/agent_orchestrator.html` (open directly in browser)
  - `http://localhost:8000/tools/agent_orchestrator.html` (when dev server is running on port 8000)
  - Click **Start fresh ↺** to load `tools/agent_orchestrator_tasks.json` into localStorage.
- **In-app Admin UI**: `http://localhost:8000/admin/agent_orchestrator.html` (requires stealth admin login)
  - Uses the in-memory API at `/api/agent-orchestrator/*` — queue wipes on server restart.
  - Click **Import JSON** to load `tools/agent_orchestrator_tasks.json` into the API store via `/batch`.

**Port is 8000** (uvicorn default). No server runs on 8088.

## Step 4: Pick the next task

Filter by **pending** + highest priority. Prefer the target model assigned by the bridge.

## Step 5: Verify the file path

The bridge guessed paths. Before dispatching, confirm the file exists at the exact path. If not, fix the path in the orchestrator task row.

## Step 6: Dispatch

1. Click **Copy** next to the task.
2. Open the assigned model session (SWE-1.7, Kimi 2.7, GLM-5.2, etc.).
3. Paste the prompt and tell the agent to work on a feature branch.
4. Update the task status to `in_progress` in the orchestrator.

## Step 7: After the agent reports back

1. Review the diff. Verify changed files compile.
2. Update the task status:

   - `resolved` if the fix is merged and verified.
   - `review` if it needs your review first.
   - `rejected` if it is not safe or not fixable.

3. Update `BUILD_STATE.md` if the task resulted in shipped code.

## Step 8: Next task

Return to Step 1 for the next task.
