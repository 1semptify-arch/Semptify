# Cons and Side Effects of the Current Sync Automation

## Commit workflow

- **Every commit now runs a sync.** This adds a few seconds to each commit. If the codebase grows, `stub_detector.py` may slow it down.
- **The hook blocks the commit if the Excel is open** in Excel or if the venv is missing. You’ll get an error and have to close the workbook or fix the environment.
- **Generated files are auto-staged.** `tools/stub_tasks_new.json`, `tools/agent_orchestrator_tasks.json`, and `Semptify_Master_Inventory_LIVE_reviewed.xlsx` will be added to every commit, even if you didn’t intend to change them.
- **Other Git hooks are bypassed.** `core.hooksPath` is now `tools/hooks`, so any hooks in `.git/hooks` are ignored unless you move them into `tools/hooks`.

## Excel workbook

- **`Stubs & TODOs` is overwritten every sync.** Any manual stub rows you add there that are not in `stub_tasks_new.json` will be lost.
- **openpyxl rewrites the entire `.xlsx` binary.** This can change formatting, drop charts, or break formulas if they exist outside the simple text cells we touched.
- **The Excel file is a binary in version control.** Regenerating it on every commit creates larger diffs and potential merge conflicts that Git cannot resolve automatically.

## Generated JSON

- **Task IDs are regenerated every run.** `agent_orchestrator_tasks.json` gets new UUIDs each time, so statuses you manually edit in the file itself are not preserved. The `agent_orchestrator.html` UI keeps its own state in `localStorage`, but the project JSON resets to `pending` each sync.
- **Line-ending churn.** `json.dumps` on Windows can produce `CRLF`, while Git may normalize to `LF`, causing noisy diffs or the “CRLF will be replaced by LF” warning.

## Orchestrator UI

- **Auto-load only works when the file is served.** It fails if you open `agent_orchestrator.html` directly with `file://` because of browser CORS. It works in Windsurf preview, VS Code Live Server, or any local HTTP server.
- **Auto-load only fills an empty localStorage.** If you already have tasks in the browser, the page does not overwrite them. You have to clear localStorage or click Clear all to pull the latest JSON.

## Environment

- **The hook hardcodes `venv311/Scripts/python.exe`.** If your venv is elsewhere or named differently, the hook will fail.
