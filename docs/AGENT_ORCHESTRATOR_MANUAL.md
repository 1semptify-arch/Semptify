# Agent Orchestrator Manual

The Agent Orchestrator queues parallel AI-agent tasks for the Semptify codebase. It turns workbook rows (stubs and duplicates) AND doc-sourced TODOs into copy-paste prompts you can drop into separate Windsurf sessions.

> **Canonical source of truth for orchestrator operation.** Last updated 2026-07-20. Supersedes older instructions in `.devin/skills/orchestrator_preflight/SKILL.md` and `BUILD_STATE.md`.

## Two UIs, same queue data

| UI | Location | Persistence | Best for |
| --- | --- | --- | --- |
| **Standalone** | `tools/agent_orchestrator.html` (open via `file://` or `http://localhost:8000/tools/agent_orchestrator.html`) | Live `agent_orchestrator_tasks.json` > embedded JSON > `localStorage` cache | Day-to-day dispatch, reloads from file on startup |
| **In-app Admin** | `http://localhost:8000/admin/agent_orchestrator.html` (stealth admin login required) | In-memory API store (`/api/agent-orchestrator/*`) | Quick create + API automation, wipes on server restart |

Use the **standalone** version for day-to-day agent dispatch. Use the **admin** version when you want to create tasks via API or import a JSON queue without touching localStorage.

## The three task sources

The orchestrator queue is fed by **three sources**, merged by `tools/sync_orchestrator.py`:

| Source | Script | Output | Purpose |
| --- | --- | --- | --- |
| **1. Stub detector** | `tools/stub_detector.py` | `tools/stub_tasks_new.json` | Scans repo for real stubs (NotImplementedError, pass, TODO markers) |
| **2. Workbook bridge** | `tools/workbook_bridge.py` | `tools/agent_orchestrator_tasks.json` (workbook rows) | Reads `Semptify_Master_Inventory_LIVE_reviewed.xlsx` for stub + duplicate rows |
| **3. Doc-sourced TODOs** | `tools/_seed_orchestrator_tasks.py` | `tools/docs_todos.json` | Compiles incomplete items from `BUILD_STATE.md`, `ACTIVE_CONTEXT.md`, `FNG_TODO.md`, `STUB_AUDIT.md` |

`sync_orchestrator.py` runs all three, merges by task `id` (workbook wins on conflict), embeds the merged JSON into `tools/agent_orchestrator.html`, and writes the final `tools/agent_orchestrator_tasks.json`.

## Quick start

### 1. Sync the queue (run all three sources + merge)

```powershell
.\venv311\Scripts\Activate.ps1
python tools/sync_orchestrator.py
```text

This produces:

- `tools/stub_tasks_new.json` (stub scan)
- `tools/docs_todos.json` (doc-sourced TODOs)
- `tools/agent_orchestrator_tasks.json` (merged queue)
- `tools/agent_orchestrator.html` (embedded JSON updated between marker comments)

### 2. Open the standalone orchestrator

- **Option A (no server):** open `file:///E:/master-repo/sources/app-semptify-fastapi/tools/agent_orchestrator.html` in any browser.
- **Option B (dev server running):** open `http://localhost:8000/tools/agent_orchestrator.html`.
- **Option C (in-app admin):** open `http://localhost:8000/admin/agent_orchestrator.html` (requires stealth admin login).

### 3. Load the queue

- **Standalone UI:** the page automatically loads the live `tools/agent_orchestrator_tasks.json` on startup (file > embedded JSON > localStorage). Click **Refresh from file ↻** to force a reload, or **Start fresh ↺** to clear `localStorage` first and then reload.
- **Admin UI:** click **Import JSON**, select `tools/agent_orchestrator_tasks.json`. Tasks POST to `/api/agent-orchestrator/batch` and persist in-memory until server restart.

### 4. Dispatch work to agents

For each task:

- Pick the assigned model in a new Windsurf session.
- Click **Copy** next to the task.
- Paste the prompt into the new session.
- When the agent finishes, mark the task **resolved** (or **rejected** if it could not be fixed cleanly).

## Heuristic model assignments

The bridge assigns models automatically:

| Workbook row | Priority | Assigned model |
| --- | --- | --- |
| HIGH stub | high | SWE-1.7 |
| MEDIUM stub | medium | SWE-1.6 |
| LOW stub | low | GLM-5.2 |
| Duplicate | high | Kimi 2.7 (long context) |
| Test stub | medium | SWE-1.6 |
| Doc stub | medium | Kimi 2.7 |
| Refactor stub | medium | SWE-1.7 |

Doc-sourced TODOs (`_seed_orchestrator_tasks.py`) set `target_model` explicitly per task. Change the model in the UI if you disagree.

## Standalone UI controls

- **Start fresh ↺** — clears localStorage and loads the newest `agent_orchestrator_tasks.json` (or embedded JSON fallback).
- **Refresh from file ↻** — re-fetch the live `agent_orchestrator_tasks.json` and overwrite the current queue without clearing `localStorage` first.
- **Create Task** — add a manual task (e.g., from a Fix-It report).
- **Status dropdown** — move a task through `pending → in_progress → review → resolved/rejected`.
- **View prompt** — read the full prompt without copying.
- **Copy** — copy prompt to clipboard.
- **Delete** — remove one task.
- **Export JSON** — back up or share the current queue.
- **Import JSON** — load a queue from the bridge or a previous export.
- **Clear all** — wipe the localStorage queue.

## Admin UI controls

- **Create Task** form — same fields as standalone, POSTs to `/api/agent-orchestrator/tasks`.
- **Task Queue** table — status dropdown + Copy prompt + Delete per row.
- **Import JSON** — reads a JSON file and POSTs each task to `/api/agent-orchestrator/batch`.
- **Export JSON** — downloads the current API queue as JSON.
- **Clear all** — deletes every task via DELETE `/api/agent-orchestrator/tasks/{id}`.

## Managing the parallel fleet

Recommended layout:

1. Open 4 Windsurf sessions side by side.
2. Assign one model per session: GLM-5.2, SWE-1.6, SWE-1.7, Kimi 2.7.
3. From the orchestrator, copy prompts and paste them into the matching model session.
4. Keep the orchestrator page visible to update statuses as agents finish.

Tip: keep tasks small and file-scoped. One task per stub or one task per duplicate pair. Large cross-module refactors should be split into multiple tasks.

## File-path notes

The bridge guesses paths as `app/modules/<filename>`. Some files actually live in `app/routers/`, `app/services/`, or `app/core/`. Before copying a prompt, check the path in the task and edit it if needed. Doc-sourced TODOs use exact paths from the source docs.

## Backup and sync

- `localStorage` is tied to the browser and origin. If you open the file from `file://`, each browser has its own storage.
- Use **Export JSON** before switching browsers or clearing data.
- `tools/agent_orchestrator_tasks.json` is regenerated by `sync_orchestrator.py` and is the canonical merge output.
- `tools/docs_todos.json` is regenerated by `_seed_orchestrator_tasks.py` and is the doc-sourced input.

## Troubleshooting

### Import JSON does nothing

- Make sure the JSON is an array of task objects.
- The sync output is a plain array; that is the expected format.

### Task counts look wrong after import

- Refresh the page or re-import. The summary updates after import.

### Prompt looks outdated after editing a task

- Edit tasks inside the UI; the prompt regenerates when you save. Currently the standalone page does not support in-place editing, so delete and re-create if the path or model needs changing.

### In-app version lost tasks

- The in-app version stores tasks in the running Python process. Restarting the server clears them. Use **Import JSON** to reload from `tools/agent_orchestrator_tasks.json`, or switch to the standalone version for persistence across restarts.

### `sync_orchestrator.py` wiped my tasks

- Old behavior: sync only merged workbook + stubs. As of 2026-07-16, sync also runs `_seed_orchestrator_tasks.py` and merges `docs_todos.json`. If you previously wrote tasks directly to `agent_orchestrator_tasks.json` (bypassing the seed), sync would overwrite them. Always write doc-sourced TODOs via `_seed_orchestrator_tasks.py` → `docs_todos.json`, not directly to the final file.

### Pre-commit hook uses wrong Python

- Fixed 2026-07-16: `.pre-commit-config.yaml` now uses `venv311/Scripts/python.exe` for all local hooks (ssot-architecture-check, guardrail-engine, sync-orchestrator). Previously used bare `python`, which resolved to Python 3.13 on Windows.

### Workflow doc says port 8088

- Fixed 2026-07-16: `.devin/skills/orchestrator_preflight/SKILL.md` now points to port 8000 (uvicorn default) and `file://` for the standalone UI. No server ever ran on 8088.

## Regenerating from the workbook or docs

When the workbook or doc TODOs are updated, re-run sync to get a fresh queue:

```powershell
python tools/sync_orchestrator.py
```

Then click **Start fresh ↺** (standalone) or **Import JSON** (admin) to reload. You can import on top of an existing queue; it will replace the loaded tasks with the freshly generated ones. If you want to keep the old queue, export it first.

## Safety rules embedded in every prompt

Every generated prompt includes the AGENTS.md rules:

- Python 3.11.9 only.
- Read `BUILD_STATE.md` and `ACTIVE_CONTEXT.md` first.
- Use `utc_now()` and specific exception handling.
- No hardcoded URLs; use `navigation.get_stage()`.
- Fix root causes, never band-aids.
- Follow the swap protocol for file rewrites.
- Verify changed files compile before ending the session.

These rules are baked into the prompt text so each agent sees them even when working in a fresh Windsurf session.

## Changelog

### 2026-07-16 — Orchestrator overhaul

#### Files changed:

- `tools/_seed_orchestrator_tasks.py` — now writes to `tools/docs_todos.json` instead of `tools/agent_orchestrator_tasks.json` (avoid sync wiping doc-sourced tasks).
- `tools/sync_orchestrator.py` — added `step_docs_todos()` and `merge_tasks()` steps. Runs all three sources (stub_detector + workbook_bridge + _seed_orchestrator_tasks) and merges by task `id` into the final `agent_orchestrator_tasks.json`. Workbook wins on id conflict.
- `.pre-commit-config.yaml` — all local hooks now use `venv311/Scripts/python.exe` instead of bare `python`. Fixes Python 3.13 vs 3.11.9 mismatch that caused hook failures.
- `.devin/skills/orchestrator_preflight/SKILL.md` — Step 3 rewritten. Port 8088 → 8000. Added `file://` option. Documented both UIs and the Import JSON button on admin.
- `static/admin/agent_orchestrator.html` — added Data card with Import JSON, Export JSON, Clear all buttons. Added `importJson()`, `exportJson()`, `clearAll()` JS functions. Admin UI can now load `agent_orchestrator_tasks.json` via `/api/agent-orchestrator/batch`.
- `docs/AGENT_ORCHESTRATOR_MANUAL.md` — this file. Full rewrite with 3-source pipeline, both UIs, troubleshooting, changelog.

#### Root causes fixed:

1. `sync_orchestrator.py` overwrote doc-sourced tasks because it only knew about workbook + stubs. Fix: added `docs_todos.json` as a third source with merge-by-id.
2. Pre-commit hooks ran on Python 3.13 (Windows App Store default) instead of 3.11.9. Fix: explicit `venv311/Scripts/python.exe` in `.pre-commit-config.yaml`.
3. Workflow doc pointed to port 8088 where no server runs. Fix: updated to 8000 + `file://`.
4. Admin UI had no import button, so the merged JSON never reached the API store. Fix: added Import JSON button + `/batch` POST wiring.
5. Two doc-sourced tasks (`todo-003`, `todo-007`) had empty `file_path`, failing sync verification. Fix: set anchor paths.

#### Verified:

- `python -m py_compile app/main.py tools/sync_orchestrator.py tools/_seed_orchestrator_tasks.py` → OK.
- `python tools/sync_orchestrator.py` → 32 tasks merged, 0 missing paths, embedded JSON updated in both HTML files.
