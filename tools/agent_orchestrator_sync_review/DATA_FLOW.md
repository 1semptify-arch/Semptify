# Agent Orchestrator Data Flow — Current State

## TL;DR

- **Canonical queue:** `tools/agent_orchestrator_tasks.json`
- **Only two active inputs:** doc-sourced TODOs (from four markdown docs) and `stub_detector.py` code scans.
- **Legacy/manual reference:** `Semptify_Master_Inventory_LIVE_reviewed.xlsx` is intentionally not auto-synced.
- **New master-level canonical state:** `E:\master-repo\tools\orchestrator_state.json` is the single source of truth for agent orchestration and routing.
- **Archived legacy tracker:** `tools/phase_c_tier2_reconciliation_tasks.json` has been archived to `E:\master-repo\archive\tools\phase_c_tier2_reconciliation_tasks.2026-08-26.json` and is no longer active.
- **Derived/embedded views:** `tools/agent_orchestrator.html`, `tools/orchestrator_dashboard.html`, `static/admin/agent_orchestrator.html`.
- **Current status:** 92 tasks in the canonical queue, 91 resolved, 1 pending (`phase2-1a1341-055`, parked).

---

## 1. Source files (human + code)

| File | Type | Purpose |
|---|---|---|
| `BUILD_STATE.md` | human markdown | "Known Broken/Pending" and "Next Session Should Start With" items. |
| `ACTIVE_CONTEXT.md` | human markdown | `NEXT TO BUILD` items and current priority narrative. |
| `docs/FNG_TODO.md` | human markdown | Unchecked design-system and feature TODOs. |
| `docs/STUB_AUDIT.md` | human markdown | Tier 1–4 stub audit list. |
| `app/**/*.py` | source code | `tools/stub_detector.py` scans for `NotImplementedError`, bare `pass`, and `# TODO` / `# stub-detector` markers. |
| `Semptify_Master_Inventory_LIVE_reviewed.xlsx` | legacy workbook | Used to be the stub/duplicate source. Its `Stubs & TODOs` and `Duplicates` sheets are now empty. Still contains reference sheets (Module/Endpoint Inventory, Task Queue, Archive) that are **not** read by the sync pipeline. |
| `tools/phase_c_tier2_reconciliation_tasks.json` | legacy JSON | 37 task definitions generated during ADR-0008 reconciliation. Not read by `sync_orchestrator.py`; exists only as a handoff artifact. |

---

## 2. Generation scripts

| Script | Reads | Writes | Runs when |
|---|---|---|---|
| `tools/stub_detector.py` | `app/` and `tests/` | `tools/stub_tasks_new.json` | Called by `sync_orchestrator.py` step 1. |
| `tools/_seed_orchestrator_tasks.py` | `BUILD_STATE.md`, `ACTIVE_CONTEXT.md`, `FNG_TODO.md`, `STUB_AUDIT.md` | `tools/docs_todos.json` | Called by `sync_orchestrator.py` step 3. |
| `tools/workbook_bridge.py` | `Semptify_Master_Inventory_LIVE_reviewed.xlsx`, `tools/stub_tasks_new.json` | `tools/agent_orchestrator_tasks.json` (intermediate, workbook rows only) | Called by `sync_orchestrator.py` step 2. |
| `tools/sync_registry.py` | `app/` modules and `app/core/product_manifest.py` | `tools/module_registry.yaml`, `tools/.sync_orchestrator_hash` | Called by `sync_orchestrator.py` step 5. |
| `tools/archive_resolved_duplicates.py` | `tools/agent_orchestrator_tasks.json`, workbook `Duplicates` sheet | Updated workbook (optional) | Manual only; not part of `sync_orchestrator.py` anymore. |
| `tools/mark_task_status.py` | `tools/agent_orchestrator_tasks.json` | `tools/agent_orchestrator_tasks.json` (status/notes/assigned_agent) | Called by agents when they pick up or finish work. |
| `tools/sync_orchestrator.py` | all of the above | `tools/agent_orchestrator_tasks.json`, embedded JSON in HTML files | Manual run or pre-commit `--check` (current pre-commit only verifies, does not regenerate). |

---

## 3. Intermediate and canonical files

| File | Role | Is canonical? | Notes |
|---|---|---|---|
| `tools/stub_tasks_new.json` | Intermediate | No | Raw stub scan output. Currently 0 stubs. |
| `tools/docs_todos.json` | Intermediate | No | Raw doc-sourced TODOs. Contains 92 tasks with **doc-derived** statuses; not the same as the final queue because it does not know about manual `mark_task_status.py` updates. |
| `tools/agent_orchestrator_tasks.json` | **Canonical queue** | **Yes** | Merged from workbook + `docs_todos.json`, then `preserve_manual_fields()` restores `status`, `notes`, `assigned_agent`, and `updated_at` from the previous run. This is what the UI and `mark_task_status.py` consume. |
| `tools/agent_orchestrator_tasks_archive.json` | Archive | No | Old resolved-task archive. Not read by any tool. |
| `tools/orchestrator_dashboard.html` | Derived view | No | Read-only dashboard with the embedded task JSON. |
| `tools/agent_orchestrator.html` | Derived view | No | Standalone orchestrator UI with embedded task JSON. |
| `static/admin/agent_orchestrator.html` | Derived view | No | Copy served by the admin route. Not auto-synced; must be copied manually if it should match `tools/`. |
| `tools/.sync_orchestrator_hash` | Generated artifact | No | Hash file used for convergence detection. Currently only referenced in a stale `todo-003` description. |

---

## 4. How the pipeline currently works

```text
BUILD_STATE.md, ACTIVE_CONTEXT.md, FNG_TODO.md, STUB_AUDIT.md
                    |
                    v
      tools/_seed_orchestrator_tasks.py
                    |
                    v
         tools/docs_todos.json (raw, 92 tasks)
                    |
app/**/*.py         |          Semptify_Master_Inventory_LIVE_reviewed.xlsx
    |               |                    |
    v               v                    v
tools/stub_detector.py  tools/workbook_bridge.py
    |                        |
    v                        v
tools/stub_tasks_new.json  tools/agent_orchestrator_tasks.json (workbook rows, currently 0)
    |                            |
    +----------+-----------------+
               |
               v
    tools/sync_orchestrator.py merge_tasks()
               |
               v
    tools/agent_orchestrator_tasks.json (merged, 92 tasks)
               |
               v
    preserve_manual_fields(previous_tasks)
               |
               v
    tools/agent_orchestrator_tasks.json (canonical, 91 resolved + 1 pending)
               |
               +----> embedded JSON in agent_orchestrator.html / orchestrator_dashboard.html
```

---

## 5. Honest consolidation/elimination proposal

The system is stabilizing after Tier 2 reconciliation. Several files now exist mainly because they were useful during the chaotic phase, not because they are needed for steady-state operation.

### 5.1 Files that can likely be eliminated

1. **`tools/agent_orchestrator_tasks_archive.json`**
   - Not read by any tool.
   - The canonical `agent_orchestrator_tasks.json` already keeps resolved tasks as history.
   - **Proposed action:** delete or move to `docs/handoffs/` as a read-only artifact.

2. **`Semptify_Master_Inventory_LIVE_reviewed.xlsx` as an auto-staged file**
   - The `Stubs & TODOs` and `Duplicates` sheets are empty; the workbook contributes 0 tasks.
   - The other sheets (Module Inventory, Endpoint Inventory, Task Queue, Archive) are manual reference data.
   - **Proposed action:** remove it from the sync pipeline entirely. Keep the file as a manual reference but do not regenerate or auto-stage it on every commit. Update `workbook_bridge.py` to no-op or be removed.

3. **`tools/.sync_orchestrator_hash`**
   - Only appears in a stale `todo-003` description. If `sync_registry.py` does not need it, it should not be tracked.
   - **Proposed action:** verify whether `sync_registry.py` still writes it, then delete if unused.

### 5.2 Files that can be simplified

1. **`tools/docs_todos.json` vs. `tools/agent_orchestrator_tasks.json`**
   - Two JSON files for one queue is confusing. `docs_todos.json` is raw input; `agent_orchestrator_tasks.json` is canonical.
   - **Proposed action (two options):**
     - **Option A (minimal):** rename `docs_todos.json` to `docs_todos_seed.json` and document that it is not canonical.
     - **Option B (consolidation):** have `_seed_orchestrator_tasks.py` write directly to `agent_orchestrator_tasks.json` and merge with stub/workbook output in memory, eliminating `docs_todos.json` from disk.
   - **Recommendation:** Option A first. Option B is a larger change and should wait until the workbook is fully retired.

2. **`static/admin/agent_orchestrator.html` vs. `tools/agent_orchestrator.html`**
   - Two copies of the same UI file. The `tools/` version is canonical; the `static/admin/` version is served.
   - **Proposed action:** either have `sync_orchestrator.py` copy/overwrite the `static/admin/` version on each run, or remove the `static/admin/` copy and configure the route to serve `tools/agent_orchestrator.html` directly.

3. **`tools/phase_c_tier2_reconciliation_tasks.json`**
   - It is a static artifact of the completed reconciliation. It should not be the source of truth for new work.
   - **Proposed action:** move to `docs/handoffs/` or `tools/archive/` and remove it from any active task generation.

### 5.3 Files that should stay

- `tools/agent_orchestrator_tasks.json` — canonical queue.
- `tools/mark_task_status.py` — the agent status update mechanism.
- `tools/sync_orchestrator.py` — single command to regenerate the queue.
- `tools/stub_detector.py` — one of the two real input sources.
- `tools/agent_orchestrator_sync_review/inspect_state.py` — useful diagnostic.

---

## 6. Open decision

Should the pre-commit hook (currently `sync_orchestrator.py --check` only) ever regenerate files, or should it remain a verification gate only? The current design (manual generation, check-only hook) is safe and avoids binary churn. The main remaining cleanup is removing the legacy files that no longer contribute to the canonical queue.
