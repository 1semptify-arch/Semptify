#!/usr/bin/env python3
"""
sync_orchestrator.py

One command that keeps stub detection, the master workbook, and the agent
orchestrator UI in sync:

    1. Runs stub_detector.py over the whole repo -> tools/stub_tasks_new.json
    2. Runs workbook_bridge.py -> tools/agent_orchestrator_tasks.json
       (reads Semptify_Master_Inventory_LIVE_reviewed.xlsx)
    3. Verifies both outputs (valid JSON, every task has a resolvable path)
    4. Embeds the tasks JSON directly into tools/agent_orchestrator.html
       (between marker comments), so the HTML works standalone from
       file:// with no fetch()/CORS problems and no server.
    5. If run as a git hook (SYNC_ORCHESTRATOR_GIT_ADD=1), re-stages the
       files it just regenerated so they're included in the commit.

Usage:
    python tools/sync_orchestrator.py            # manual run
    python tools/sync_orchestrator.py --check    # verify only, no writes (CI)

Exit codes: 0 = success, 1 = a step failed or verification failed.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
MASTER_ORCHESTRATOR_STATE = REPO_ROOT.parent.parent / "tools" / "orchestrator_state.json"
MASTER_ORCHESTRATOR_STATE = REPO_ROOT.parent.parent / "tools" / "orchestrator_state.json"

STUB_DETECTOR = TOOLS_DIR / "stub_detector.py"
WORKBOOK_BRIDGE = TOOLS_DIR / "workbook_bridge.py"
DOCS_TODO_SEED = TOOLS_DIR / "_seed_orchestrator_tasks.py"
STUB_TASKS_OUT = TOOLS_DIR / "stub_tasks_new.json"
DOCS_TODOS_OUT = TOOLS_DIR / "docs_todos.json"
ORCHESTRATOR_TASKS = TOOLS_DIR / "agent_orchestrator_tasks.json"
ORCHESTRATOR_HTML = TOOLS_DIR / "agent_orchestrator.html"
DASHBOARD_HTML = TOOLS_DIR / "orchestrator_dashboard.html"
SYNC_REGISTRY = TOOLS_DIR / "sync_registry.py"
WORKBOOK_XLSX = REPO_ROOT / "Semptify_Master_Inventory_LIVE_reviewed.xlsx"

EMBED_START = "<!-- SYNC_ORCHESTRATOR:TASKS_START -->"
EMBED_END = "<!-- SYNC_ORCHESTRATOR:TASKS_END -->"


class SyncError(RuntimeError):
    pass


def run(cmd: list[str], label: str) -> None:
    print(f"-> {label}: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)  # noqa: S603 # nosec B603
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        raise SyncError(f"{label} failed (exit {result.returncode})")


def step_stub_detector() -> None:
    if not STUB_DETECTOR.exists():
        raise SyncError(f"missing {STUB_DETECTOR}")
    run(
        [sys.executable, str(STUB_DETECTOR), ".", "--out", str(STUB_TASKS_OUT)],
        "stub_detector.py",
    )


def step_workbook_bridge() -> None:
    if not WORKBOOK_BRIDGE.exists():
        raise SyncError(f"missing {WORKBOOK_BRIDGE}")
    if not WORKBOOK_XLSX.exists():
        raise SyncError(f"missing {WORKBOOK_XLSX.name} at repo root — workbook_bridge.py needs it")
    run([sys.executable, str(WORKBOOK_BRIDGE)], "workbook_bridge.py")


def step_sync_registry() -> None:
    if not SYNC_REGISTRY.exists():
        raise SyncError(f"missing {SYNC_REGISTRY}")
    run([sys.executable, str(SYNC_REGISTRY), "--write"], "sync_registry.py")


def step_docs_todos() -> None:
    """Run _seed_orchestrator_tasks.py to produce docs_todos.json.

    This is the third source: doc-sourced TODOs from BUILD_STATE.md,
    ACTIVE_CONTEXT.md, FNG_TODO.md, and STUB_AUDIT.md. Writes to
    tools/docs_todos.json, which merge_tasks() combines with workbook
    output into the final agent_orchestrator_tasks.json.

    The raw seed prints its own status summary, but that does not reflect
    the final canonical queue after merge and manual-field preservation.
    We suppress the seed's stdout here and print a canonical summary later.
    """
    if not DOCS_TODO_SEED.exists():
        print(f"-> skipping docs_todos (missing {DOCS_TODO_SEED.name})")
        return
    print(f"-> _seed_orchestrator_tasks.py: {sys.executable} {DOCS_TODO_SEED}")
    result = subprocess.run(
        [sys.executable, str(DOCS_TODO_SEED)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )  # noqa: S603 # nosec B603
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise SyncError("_seed_orchestrator_tasks.py failed")
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)


def _load_previous_tasks() -> list[dict]:
    """Load the existing agent_orchestrator_tasks.json before it is regenerated."""
    if not ORCHESTRATOR_TASKS.exists():
        return []
    try:
        data = json.loads(ORCHESTRATOR_TASKS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("created", data.get("tasks", []))
    return []


def preserve_manual_fields(previous_tasks: list[dict]) -> int:
    """Carry forward human-edited fields from the previous task queue.

    sync_orchestrator regenerates task metadata from the workbook and doc
    sources, which resets manually-set status/notes/assigned_agent timestamps.
    This restores those fields for any task whose id still exists in the
    freshly generated queue.
    """
    if not previous_tasks:
        return 0
    prev_by_id = {t.get("id"): t for t in previous_tasks if t.get("id")}
    if not prev_by_id:
        return 0

    try:
        tasks = json.loads(ORCHESTRATOR_TASKS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(tasks, list):
        return 0

    preserved = 0
    preserved_fields = ("status", "notes", "assigned_agent", "created_at", "updated_at")
    for task in tasks:
        prev = prev_by_id.get(task.get("id"))
        if not prev:
            continue
        for field in preserved_fields:
            if field in prev:
                task[field] = prev[field]
        preserved += 1

    new_content = json.dumps(tasks, indent=2) + "\n"
    old_content = ORCHESTRATOR_TASKS.read_text(encoding="utf-8") if ORCHESTRATOR_TASKS.exists() else ""
    if new_content != old_content:
        ORCHESTRATOR_TASKS.write_text(new_content, encoding="utf-8", newline="\n")
        print(f"-> preserved manual fields for {preserved} task(s) in {ORCHESTRATOR_TASKS.name}")
    return preserved


def merge_tasks() -> int:
    """Merge workbook tasks + docs_todos.json into agent_orchestrator_tasks.json.

    workbook_bridge.py writes agent_orchestrator_tasks.json with stub/duplicate
    tasks. This step reads docs_todos.json (if present), merges by task id, and
    writes the combined list back. Dedup by id: workbook tasks win on conflict.
    """
    try:
        workbook_data = json.loads(ORCHESTRATOR_TASKS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        workbook_data = []
    if not isinstance(workbook_data, list):
        workbook_data = (
            workbook_data.get("created", workbook_data.get("tasks", [])) if isinstance(workbook_data, dict) else []
        )

    docs_data = []
    if DOCS_TODOS_OUT.exists():
        try:
            docs_data = json.loads(DOCS_TODOS_OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"-> WARNING: {DOCS_TODOS_OUT.name} is not valid JSON: {e}")
            docs_data = []
        if not isinstance(docs_data, list):
            docs_data = []

    seen_ids = {t.get("id") for t in workbook_data if isinstance(t, dict)}
    merged = list(workbook_data)
    added = 0
    for t in docs_data:
        if isinstance(t, dict) and t.get("id") not in seen_ids:
            merged.append(t)
            seen_ids.add(t.get("id"))
            added += 1

    new_content = json.dumps(merged, indent=2) + "\n"
    old_content = ORCHESTRATOR_TASKS.read_text(encoding="utf-8") if ORCHESTRATOR_TASKS.exists() else ""
    if new_content != old_content:
        ORCHESTRATOR_TASKS.write_text(new_content, encoding="utf-8", newline="\n")
        print(f"-> merged {added} doc-sourced task(s) into {ORCHESTRATOR_TASKS.name} (total: {len(merged)})")
    else:
        print(f"-> {ORCHESTRATOR_TASKS.name} already up to date ({len(merged)} tasks)")
    return len(merged)


def verify_stub_tasks() -> int:
    if not STUB_TASKS_OUT.exists():
        raise SyncError(f"{STUB_TASKS_OUT} was not produced")
    try:
        data = json.loads(STUB_TASKS_OUT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SyncError(f"{STUB_TASKS_OUT} is not valid JSON: {e}")
    if not isinstance(data, list):
        raise SyncError(f"{STUB_TASKS_OUT} should be a JSON list of stub tasks")
    for i, task in enumerate(data):
        if not task.get("file"):
            raise SyncError(f"stub task #{i} is missing a 'file' path")
    return len(data)


def verify_orchestrator_tasks() -> tuple[int, int]:
    if not ORCHESTRATOR_TASKS.exists():
        raise SyncError(f"{ORCHESTRATOR_TASKS} was not produced")
    try:
        data = json.loads(ORCHESTRATOR_TASKS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SyncError(f"{ORCHESTRATOR_TASKS} is not valid JSON: {e}")
    tasks = data if isinstance(data, list) else data.get("created", data.get("tasks", []))
    if not isinstance(tasks, list):
        raise SyncError(f"{ORCHESTRATOR_TASKS} has no recognizable task list")
    missing_paths = [t for t in tasks if not t.get("file_path")]
    if missing_paths:
        raise SyncError(f"{len(missing_paths)} orchestrator task(s) have no file_path field")
    return len(tasks), len(missing_paths)


def embed_tasks_into_html(tasks_json_text: str, target: Path) -> None:
    if not target.exists():
        raise SyncError(f"missing {target}")
    html = target.read_text(encoding="utf-8")

    block = (
        f"{EMBED_START}\n"
        f'<script type="application/json" id="embedded-tasks">\n'
        f"{tasks_json_text}\n"
        f"</script>\n"
        f"{EMBED_END}"
    )

    if EMBED_START in html and EMBED_END in html:
        pre = html.split(EMBED_START)[0]
        post = html.split(EMBED_END)[1]
        new_html = pre + block + post
    else:
        # First run: insert the block right before the main <script> tag.
        # This MUST come before the app's own <script>, not before
        # </body> — loadTasks() reads #embedded-tasks at script parse
        # time, before the browser has parsed anything later in the
        # document, so the data element has to already exist above it.
        if "<script>" not in html:
            raise SyncError(f"{target} has no <script> tag to anchor the embed")
        new_html = html.replace("<script>", block + "\n<script>", 1)

    if new_html != html:
        target.write_text(new_html, encoding="utf-8", newline="\n")
        print(f"-> embedded tasks JSON into {target.name}")
    else:
        print(f"-> {target.name} already up to date")


def git_add(paths: list[Path]) -> None:
    existing = [str(p) for p in paths if p.exists()]
    if not existing:
        return
    run(["git", "add", *existing], "git add (re-stage synced files)")




def _is_semtify_task(task: dict) -> bool:
    """Return True if a master orchestrator task belongs in the Semptify legacy queue.

    Master queue is repo-wide. The Semptify legacy queue should only carry tasks
    whose file_path is inside Semptify FastAPI, Semptify-PI, or Semptify root
    docs/tools, not generic master-repo work.
    """
    fp = task.get("file_path") or ""
    if not fp:
        return False
    tid = task.get("id", "")
    if tid in {
        "non-semtify-modules-loose-ends-2026-08-29",
        "master-state-docs-loose-ends-2026-08-29",
    }:
        return False

    # Exclude master module scans and master-only docs.
    if fp.startswith(("modules/", "modules\\")) and not fp.startswith(
        ("modules/app-semptify-fastapi", "modules\\app-semptify-fastapi")
    ):
        return False
    if fp.startswith(("docs/", "docs\\")):
        return False

    # Allow absolute paths only under Semptify FastAPI or Semptify-PI.
    if fp.startswith("C:") or fp.startswith("/"):
        norm = fp.replace("\\", "/").lower()
        return (
            "/master-repo/modules/app-semptify-fastapi/" in norm
            or "/master-repo/sources/app-semptify-pi/" in norm
        )

    return True


def _map_master_to_legacy(task: dict) -> dict:
    """Map master orchestrator_state.json schema to legacy agent_orchestrator_tasks.json schema."""
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "description": task.get("description"),
        "file_path": task.get("file_path"),
        "priority": task.get("priority"),
        "status": task.get("status"),
        "category": task.get("category", "other"),
        "notes": task.get("notes", ""),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
        "target_model": task.get("model_tier") or "unassigned",
        "assigned_agent": task.get("assigned_to") or "unassigned",
    }


def step_master_sync() -> int:
    """Pull Semptify tasks from the canonical master orchestrator queue.

    The master queue (C:\\master-repo\\tools\\orchestrator_state.json) is the
    canonical source of truth. This step merges any Semptify-specific tasks
    from master into the local agent_orchestrator_tasks.json so the legacy
    queue does not diverge or get wiped by the workbook-only path.
    """
    if not MASTER_ORCHESTRATOR_STATE.exists():
        print(f"-> skipping master sync (not found: {MASTER_ORCHESTRATOR_STATE})")
        return 0

    with MASTER_ORCHESTRATOR_STATE.open("r", encoding="utf-8") as f:
        master_data = json.load(f)
    master_tasks = master_data.get("tasks", [])

    semtify_tasks = [_map_master_to_legacy(t) for t in master_tasks if _is_semtify_task(t)]
    if not semtify_tasks:
        print("-> no Semptify tasks found in master queue")
        return 0

    current_data = []
    if ORCHESTRATOR_TASKS.exists():
        try:
            current_data = json.loads(ORCHESTRATOR_TASKS.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            current_data = []
    if not isinstance(current_data, list):
        current_data = (
            current_data.get("created", current_data.get("tasks", []))
            if isinstance(current_data, dict)
            else []
        )

    current_by_id = {t.get("id"): t for t in current_data if t.get("id")}
    updated = 0
    added = 0
    for mt in semtify_tasks:
        if mt["id"] in current_by_id:
            # Master wins for status and core fields; keep any extra legacy fields.
            existing = current_by_id[mt["id"]]
            existing.update({k: v for k, v in mt.items() if v is not None})
            updated += 1
        else:
            current_data.append(mt)
            current_by_id[mt["id"]] = mt
            added += 1

    new_content = json.dumps(current_data, indent=2) + "\n"
    ORCHESTRATOR_TASKS.write_text(new_content, encoding="utf-8", newline="\n")
    print(
        f"-> master sync: {added} new, {updated} updated Semptify task(s) in "
        f"{ORCHESTRATOR_TASKS.name} (total: {len(current_data)})"
    )
    return len(current_data)

def print_task_summary(path: Path, label: str) -> None:
    """Print a human-readable status summary for a task JSON list."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(data, list):
        return
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for t in data:
        by_status[t.get("status", "unknown")] = by_status.get(t.get("status", "unknown"), 0) + 1
        by_priority[t.get("priority", "unknown")] = by_priority.get(t.get("priority", "unknown"), 0) + 1
    print(f"\n{label}: {len(data)} tasks")
    print(f"  by status: {by_status}")
    print(f"  by priority: {by_priority}")
    pending = [t for t in data if t.get("status") != "resolved"]
    if pending:
        print(f"  non-resolved ({len(pending)}):")
        for t in pending[:10]:
            title = t.get("title", "")
            print(f"    {t['id']} [{t.get('priority', '?')}] {title[:80]}{'...' if len(title) > 80 else ''}")
        if len(pending) > 10:
            print(f"    ... and {len(pending) - 10} more")
    else:
        print("  no non-resolved tasks — queue is clear")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify existing outputs only; don't regenerate anything (for CI).",
    )
    parser.add_argument(
        "--git-add",
        action="store_true",
        help="Re-stage regenerated files with `git add` after syncing (for the pre-commit hook).",
    )
    args = parser.parse_args()

    try:
        if not args.check:
            previous_tasks = _load_previous_tasks()
            step_stub_detector()
            step_workbook_bridge()
            step_docs_todos()
            merge_tasks()
            preserve_manual_fields(previous_tasks)
            step_master_sync()
            print_task_summary(ORCHESTRATOR_TASKS, "Final canonical queue")
            step_sync_registry()

        stub_count = verify_stub_tasks()
        task_count, missing = verify_orchestrator_tasks()

        if not args.check:
            tasks_text = ORCHESTRATOR_TASKS.read_text(encoding="utf-8")
            embed_tasks_into_html(tasks_text, ORCHESTRATOR_HTML)
            if DASHBOARD_HTML.exists():
                embed_tasks_into_html(tasks_text, DASHBOARD_HTML)

        print(
            f"\nOK: {stub_count} stub(s) in {STUB_TASKS_OUT.name}, "
            f"{task_count} task(s) in {ORCHESTRATOR_TASKS.name} "
            f"({missing} missing paths)."
        )

        if args.git_add and not args.check:
            git_add([STUB_TASKS_OUT, ORCHESTRATOR_TASKS, ORCHESTRATOR_HTML, DASHBOARD_HTML])

        return 0
    except SyncError as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
