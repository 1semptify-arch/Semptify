# Orchestrator Sync Pipeline — Operations Guide

This is the complete reference for keeping the stub/task/workbook/GUI system
in sync. Read this before touching any of the files below.

## The files, what each one is

| File | What it does | Who runs it | When |
| --- | --- | --- | --- |
| `tools/stub_detector.py` | Scans the codebase, finds real stubs (AST-based, not grep) | `sync_orchestrator.py` calls it | Every sync |
| `tools/workbook_bridge.py` | Reads stubs + the workbook's `Duplicates` sheet, merges against the previous run, writes `agent_orchestrator_tasks.json` | `sync_orchestrator.py` calls it | Every sync |
| `tools/sync_orchestrator.py` | Runs the two above in order, verifies the output, embeds it into both HTML views | **A human or the pre-commit hook** | Every commit (automatic) + any time you want a manual refresh |
| `tools/mark_task_status.py` | Updates ONE task's status/notes/agent, safely under concurrent writes | **Agents, directly** | The instant an agent picks up or finishes a task |
| `tools/archive_resolved_duplicates.py` | Moves resolved/rejected duplicate rows out of the `Duplicates` sheet into an `Archive` sheet, drops them from the active queue | **A human, deliberately** | Periodically — never automatic |
| `tools/agent_orchestrator.html` | The working queue — pick a task, copy its prompt, see status | Anyone, opened in a browser | Whenever you're working tasks |
| `tools/orchestrator_dashboard.html` | Read-only overview — counts, breakdowns by status/category/agent, filterable table | Anyone, opened in a browser | Whenever you want the big picture |

## Source of truth for each piece of data

- **What stubs exist right now** → the code itself, via `stub_detector.py`. Never hand-edit `stub_tasks_new.json`.
- **What duplicates need resolving** → the workbook's `Duplicates` sheet. This is the human-maintained list — add/remove rows there directly if the actual duplicate-code situation changes.
- **Task status, notes, which agent is on it** → `agent_orchestrator_tasks.json`, edited by `mark_task_status.py`. This survives re-syncs by design (tasks are matched by a stable content-derived ID, not a random one, so a re-sync doesn't wipe your progress).
- **Historical record of resolved duplicates** → the workbook's `Archive` sheet, populated by `archive_resolved_duplicates.py`.

## The rule for agents (put this in AGENTS.md / CLAUDE.md)

> Whenever you pick up a task from `agent_orchestrator_tasks.json`, immediately run:
> `python tools/mark_task_status.py <task_id> in_progress --agent <your-model-name>`
>
> When you finish:
> `python tools/mark_task_status.py <task_id> resolved --notes "<one-line summary>" --agent <your-model-name>`
>
> If you get blocked, use `review` instead of `resolved` and explain why in `--notes`. Do this every time, without being asked — it's how the queue stays accurate without a human tracking it by hand.

## Full refresh — the complete order

Run these from the repo root, in this order, any time you want everything
fully current (e.g., after a batch of agents have been working, or before a
status meeting with yourself):

```text
1. python tools/sync_orchestrator.py
   -> rebuilds stubs, rebuilds tasks from the workbook, merges statuses
      forward, embeds fresh data into both HTML files.

2. python tools/archive_resolved_duplicates.py --dry-run
   -> shows you what's resolved/rejected and ready to clear out.
      Nothing is changed yet.

3. python tools/archive_resolved_duplicates.py
   -> (only if step 2's preview looks right) actually moves those rows
      into the workbook's Archive sheet and drops them from the queue.

4. python tools/sync_orchestrator.py
   -> run again so the HTML embeds reflect the archive from step 3.
      (Step 1's embed is now one step stale — this catches it up.)

5. Open tools/orchestrator_dashboard.html and tools/agent_orchestrator.html
   in a browser (or reload if already open) to see the current state.
```

Steps 2–3 are optional on any given refresh — skip them if there's nothing
to archive yet. Steps 1, 4, and 5 are the ones worth doing every time.

## What's automatic vs. manual, and why

- **Automatic (pre-commit hook, every commit):** `sync_orchestrator.py` only.
  It never touches the workbook's binary content and never archives
  anything — it's safe to run unattended because it can't destroy manual
  work or lose data.
- **Manual only:** `workbook_bridge.py --update-workbook` (writes stub data
  back into the `Stubs & TODOs` sheet — rewrites the whole `.xlsx` binary,
  can drop formatting, fails if Excel has the file open) and
  `archive_resolved_duplicates.py` (permanently edits the human-maintained
  `Duplicates` sheet). Both are deliberate, occasional actions a person
  chooses to run — never wired into the hook.

## Common situations

### "A task is marked resolved but keeps showing up."

Expected until you run `archive_resolved_duplicates.py` — resolved tasks
stay visible (correctly marked) until someone deliberately clears them,
because the underlying workbook row is still there. Run the archive step.

**"I made a manual edit to `agent_orchestrator_tasks.json` and I'm worried
the next sync will wipe it."**
It won't, as long as the task's `file_path` + `title` didn't change —
that's what the stable ID is derived from. `status`, `notes`, and
`assigned_agent` are explicitly preserved across every re-sync.

### "The workbook is open in Excel and a script failed."

Only `--update-workbook` and `archive_resolved_duplicates.py` touch the
`.xlsx` file. Close Excel and re-run. The default `sync_orchestrator.py`
path never opens the workbook for writing, so this shouldn't come up
during normal commits.
