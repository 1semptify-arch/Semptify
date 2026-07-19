#!/usr/bin/env python3
"""Mark a single task's status in tools/agent_orchestrator_tasks.json.

Built so an AI agent can call this itself the moment it picks up or finishes
a task, instead of relying on a human to remember to update the queue.

Usage:
    python tools/mark_task_status.py <task_id> <status> [--notes "..."] [--agent "kimi-2.7"]

Valid statuses: pending, in_progress, review, resolved, rejected

Examples:
    # Agent picks up a task
    python tools/mark_task_status.py d0ddc6f7b028 in_progress --agent kimi-2.7

    # Agent finishes it
    python tools/mark_task_status.py d0ddc6f7b028 resolved --notes "Fixed empty return in case_builder.py, added test"

This is safe to call from multiple agents/processes at once: it takes a
plain file-based lock (portable to Windows) around the read-modify-write so
two agents finishing tasks at the same moment don't overwrite each other's
change to the same JSON file.
"""

import argparse
import contextlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

VALID_STATUSES = {"pending", "in_progress", "review", "resolved", "rejected"}

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = REPO_ROOT / "tools" / "agent_orchestrator_tasks.json"
LOCK_PATH = REPO_ROOT / "tools" / ".agent_orchestrator_tasks.lock"


def acquire_lock(timeout: float = 10.0, poll: float = 0.05) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(fd)
            return
        except FileExistsError:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Could not acquire lock {LOCK_PATH} within {timeout}s — "
                    "another process may be stuck; delete the .lock file if so."
                )
            time.sleep(poll)


def release_lock() -> None:
    with contextlib.suppress(FileNotFoundError):
        LOCK_PATH.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_id", help="The 'id' field of the task (from agent_orchestrator_tasks.json)")
    parser.add_argument("status", choices=sorted(VALID_STATUSES))
    parser.add_argument("--notes", default=None, help="Optional note to attach (appended, not overwritten)")
    parser.add_argument("--agent", default=None, help="Which agent/model made this change, e.g. 'kimi-2.7'")
    args = parser.parse_args()

    if not TASKS_PATH.exists():
        print(f"Not found: {TASKS_PATH}", file=sys.stderr)
        return 1

    acquire_lock()
    try:
        tasks = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
        match = next((t for t in tasks if t.get("id") == args.task_id), None)
        if match is None:
            print(f"No task with id {args.task_id!r} found in {TASKS_PATH.name}", file=sys.stderr)
            return 1

        old_status = match.get("status")
        match["status"] = args.status
        match["updated_at"] = datetime.now(UTC).isoformat()
        if args.agent:
            match["assigned_agent"] = args.agent
        if args.notes:
            existing = match.get("notes", "")
            stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
            entry = f"[{stamp}{' - ' + args.agent if args.agent else ''}] {args.notes}"
            match["notes"] = f"{existing}\n{entry}".strip() if existing else entry

        TASKS_PATH.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Task {args.task_id}: {old_status} -> {args.status}")
        if args.notes:
            print(f"  note added: {args.notes}")
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
