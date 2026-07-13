# Prompt for an Outside Source

## Context

We have a FastAPI repo that uses an Agent Orchestrator to track stub fixes and duplicate-resolution tasks. The files involved are:

- `tools/stub_detector.py` — AST-based scanner that finds real stubs and writes `tools/stub_tasks_new.json`.
- `tools/workbook_bridge.py` — reads `tools/stub_tasks_new.json`, writes the stubs back to `Semptify_Master_Inventory_LIVE_reviewed.xlsx` (`Stubs & TODOs` sheet), then reads `Stubs & TODOs` and `Duplicates` to generate `tools/agent_orchestrator_tasks.json`.
- `tools/agent_orchestrator.html` — standalone localStorage-based UI that loads `tools/agent_orchestrator_tasks.json`.
- `tools/sync_orchestrator.py` — one-command pipeline: `stub_detector.py` then `workbook_bridge.py`.
- `tools/hooks/pre-commit` — Git pre-commit hook that runs `sync_orchestrator.py` and re-stages the generated files.

## Current Verified State

- `stub_tasks_new.json`: 0 stubs
- `agent_orchestrator_tasks.json`: 16 tasks (0 stubs, 16 duplicates)
- `Semptify_Master_Inventory_LIVE_reviewed.xlsx`: `Stubs & TODOs` cleared, `Duplicates` intact
- `git config core.hooksPath` is set to `tools/hooks`

## Cons We Already See

1. Pre-commit hook runs on every commit and blocks commits if the Excel workbook is open or if the venv is missing.
2. Generated files are auto-staged on every commit, including a binary `.xlsx` workbook, causing large diffs and merge conflicts.
3. `Stubs & TODOs` sheet is overwritten every sync, losing manual stub entries.
4. `openpyxl` rewrites the entire `.xlsx` binary and may drop formatting/charts/formulas.
5. `agent_orchestrator_tasks.json` gets new UUIDs every run, losing manually edited statuses.
6. `agent_orchestrator.html` auto-load only works when the file is served (not via `file://`), and only when localStorage is empty.
7. The hook hardcodes `venv311/Scripts/python.exe`.

## The Ask

Propose a better architecture for keeping these three artifacts in sync. Requirements:

- Avoid binary churn in Git.
- Do not block commits if the Excel workbook is open.
- Keep the `Duplicates` task list usable (currently in the workbook `Duplicates` sheet).
- Keep the `agent_orchestrator.html` UI reasonably up to date without requiring a manual import every time.
- Preserve task statuses across syncs when possible, or explain why you would not.
- Stay compatible with Python 3.11.9 and the existing `Semptify_Master_Inventory_LIVE_reviewed.xlsx` workbook if it is still used.

Please provide:

1. A recommended architecture (data flow, source of truth).
2. Which files should be generated, which should be committed, and which should be ignored.
3. A concrete implementation plan with the files/scripts that need to change.
4. Any trade-offs with the new approach.

You can inspect the current state by running `python tools/agent_orchestrator_sync_review/inspect_state.py` from the repo root.
