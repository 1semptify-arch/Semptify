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

STUB_DETECTOR = TOOLS_DIR / "stub_detector.py"
WORKBOOK_BRIDGE = TOOLS_DIR / "workbook_bridge.py"
STUB_TASKS_OUT = TOOLS_DIR / "stub_tasks_new.json"
ORCHESTRATOR_TASKS = TOOLS_DIR / "agent_orchestrator_tasks.json"
ORCHESTRATOR_HTML = TOOLS_DIR / "agent_orchestrator.html"
DASHBOARD_HTML = TOOLS_DIR / "orchestrator_dashboard.html"
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
        target.write_text(new_html, encoding="utf-8")
        print(f"-> embedded tasks JSON into {target.name}")
    else:
        print(f"-> {target.name} already up to date")


def git_add(paths: list[Path]) -> None:
    existing = [str(p) for p in paths if p.exists()]
    if not existing:
        return
    run(["git", "add", *existing], "git add (re-stage synced files)")


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
            step_stub_detector()
            step_workbook_bridge()

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
