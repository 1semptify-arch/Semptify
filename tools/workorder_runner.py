#!/usr/bin/env python3
"""workorder_runner.py — claim, complete, and reject tasks from agent_orchestrator_tasks.json safely for concurrent agents.

Usage:
    .\\venv311\\Scripts\\Activate.ps1
    python tools/workorder_runner.py --agent swe-1.6 claim
    python tools/workorder_runner.py --agent swe-1.6 done <task_id>
    python tools/workorder_runner.py --agent swe-1.6 reject <task_id> --reason "duplicate of xyz"
    python tools/workorder_runner.py status

Note: --agent is a global flag that must come BEFORE the subcommand.

Lifecycle:
    pending --> in_progress --> done (terminal for agents)
                              \\-> rejected (invalid/duplicate/wrong-scope)
    Brad manually moves done --> resolved or rejected via the HTML UI.
    Agents do NOT self-promote to review — Brad reviews done work.

Environment:
    AGENT_NAME — default agent name used in `claimed_by`.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from filelock import FileLock, Timeout

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.utc import parse_iso, utc_now  # noqa: E402

DEFAULT_TASKS_PATH = REPO_ROOT / "tools" / "agent_orchestrator_tasks.json"
DEFAULT_TIMEOUT_MINUTES = 60


def _tasks_path(value: str | None) -> Path:
    return Path(value) if value else DEFAULT_TASKS_PATH


def _lock_path(tasks_path: Path) -> Path:
    return tasks_path.with_suffix(tasks_path.suffix + ".lock")


def _load_tasks(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_tasks(path: Path, tasks: list[dict]) -> None:
    path.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _now_iso() -> str:
    return utc_now().isoformat()


def _claim(task: dict, agent_name: str) -> None:
    now = _now_iso()
    task["status"] = "in_progress"
    task["claimed_by"] = {"agent": agent_name, "claimed_at": now}
    task["updated_at"] = now


def _is_stale_claim(task: dict, timeout_minutes: int) -> bool:
    claimed_by = task.get("claimed_by") or {}
    claimed_at = claimed_by.get("claimed_at")
    if not claimed_at:
        return True
    try:
        claimed_dt = parse_iso(claimed_at)
    except Exception:
        return True
    elapsed = (utc_now() - claimed_dt).total_seconds()
    return elapsed > timeout_minutes * 60


def _find_next_claimable(tasks: list[dict], timeout_minutes: int) -> dict | None:
    """Return the first task an agent is allowed to claim.

    Order of preference:
        1. `pending`
        2. `in_progress` with a stale claim (older than timeout)
        3. `in_progress` with a recent claim is skipped so another agent owns it.
    """
    for task in tasks:
        status = task.get("status")
        if status == "pending":
            return task
        if status == "in_progress" and _is_stale_claim(task, timeout_minutes):
            return task
    return None


def claim_next_pending(
    tasks_path: Path,
    agent_name: str,
    timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES,
) -> dict | None:
    """Atomically claim the next available task.

    Uses a file lock so only one agent can claim at a time.
    Returns the claimed task, or None if nothing is claimable.
    """
    if not tasks_path.exists():
        raise FileNotFoundError(tasks_path)

    lock = FileLock(str(_lock_path(tasks_path)), timeout=10)
    try:
        with lock:
            tasks = _load_tasks(tasks_path)
            task = _find_next_claimable(tasks, timeout_minutes)
            if task is None:
                return None
            _claim(task, agent_name)
            _save_tasks(tasks_path, tasks)
            return task
    except Timeout as e:
        raise RuntimeError("Could not acquire task lock; another agent is claiming.") from e


def mark_done(
    tasks_path: Path,
    task_id: str,
    agent_name: str,
) -> dict | None:
    """Atomically mark a task as done.

    Requires the caller's agent name to match the task's claimed_by.agent.
    Prevents one agent from silently marking another agent's task as done.
    """
    if not tasks_path.exists():
        raise FileNotFoundError(tasks_path)

    lock = FileLock(str(_lock_path(tasks_path)), timeout=10)
    with lock:
        tasks = _load_tasks(tasks_path)
        for task in tasks:
            if task.get("id") == task_id:
                claimed_by = task.get("claimed_by") or {}
                claimant = claimed_by.get("agent") if isinstance(claimed_by, dict) else None
                if claimant and claimant != agent_name:
                    raise PermissionError(
                        f"Task {task_id} is claimed by '{claimant}', not '{agent_name}'. "
                        f"Only the claiming agent can mark it done."
                    )
                if not claimant:
                    raise PermissionError(
                        f"Task {task_id} is not claimed. Claim it first with: "
                        f"python tools/workorder_runner.py --agent {agent_name} claim"
                    )
                task["status"] = "done"
                task["updated_at"] = _now_iso()
                _save_tasks(tasks_path, tasks)
                return task
    return None


def reject_task(
    tasks_path: Path,
    task_id: str,
    agent_name: str,
    reason: str = "",
) -> dict | None:
    """Atomically mark a task as rejected.

    Used when an agent discovers a task is invalid (duplicate, already fixed,
    wrong scope, etc.) and should not be worked on. Any agent can reject any
    pending or in_progress task — this is not a claim-gated operation because
    an agent might reject a task they just claimed without wanting to 'done' it.

    Rejecting a task that is already 'done' or 'rejected' is a no-op error.
    """
    if not tasks_path.exists():
        raise FileNotFoundError(tasks_path)

    lock = FileLock(str(_lock_path(tasks_path)), timeout=10)
    with lock:
        tasks = _load_tasks(tasks_path)
        for task in tasks:
            if task.get("id") == task_id:
                current_status = task.get("status", "pending")
                if current_status in ("done", "rejected"):
                    raise ValueError(
                        f"Task {task_id} is already '{current_status}'. " f"Cannot reject a finished task."
                    )
                task["status"] = "rejected"
                task["rejected_by"] = {
                    "agent": agent_name,
                    "reason": reason,
                    "rejected_at": _now_iso(),
                }
                task["updated_at"] = _now_iso()
                _save_tasks(tasks_path, tasks)
                return task
    return None


def _status_summary(tasks_path: Path) -> dict:
    tasks = _load_tasks(tasks_path)
    counts = {}
    for task in tasks:
        status = task.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {"total": len(tasks), "by_status": counts}


def _default_agent() -> str:
    return os.environ.get("AGENT_NAME") or "anonymous"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tasks",
        type=Path,
        default=DEFAULT_TASKS_PATH,
        help="Path to agent_orchestrator_tasks.json (default: tools/agent_orchestrator_tasks.json).",
    )
    parser.add_argument(
        "--agent",
        default=_default_agent(),
        help="Agent/model name written into claimed_by (default: AGENT_NAME env or 'anonymous').",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_MINUTES,
        help="Minutes before an in_progress claim is considered abandoned (default: 60).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    claim = sub.add_parser("claim", help="Claim the next pending/stale task.")
    claim.add_argument(
        "--json",
        action="store_true",
        help="Print the full task JSON instead of a summary.",
    )

    done = sub.add_parser("done", help="Mark a task as done (must be claimed by you).")
    done.add_argument("task_id", help="ID of the task to mark done.")

    reject = sub.add_parser("reject", help="Reject a task as invalid/duplicate/wrong-scope.")
    reject.add_argument("task_id", help="ID of the task to reject.")
    reject.add_argument(
        "--reason",
        default="",
        help="Short reason for rejection (e.g. 'duplicate of task xyz', 'already fixed in commit abc').",
    )

    sub.add_parser("status", help="Show task counts by status.")

    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.command == "status":
        summary = _status_summary(args.tasks)
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "claim":
        try:
            task = claim_next_pending(args.tasks, args.agent, timeout_minutes=args.timeout)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if task is None:
            print("No claimable task found (all done or in progress).")
            return 2

        if args.json:
            print(json.dumps(task, indent=2))
        else:
            print(
                f"Claimed [{task.get('id')}] {task.get('title')} "
                f"for {task['claimed_by']['agent']} at {task['claimed_by']['claimed_at']}"
            )
        return 0

    if args.command == "done":
        try:
            task = mark_done(args.tasks, args.task_id, args.agent)
        except (FileNotFoundError, PermissionError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        if task is None:
            print(f"Task not found: {args.task_id}", file=sys.stderr)
            return 1
        print(f"Marked done: {task.get('title')} ({task.get('id')})")
        return 0

    if args.command == "reject":
        try:
            task = reject_task(args.tasks, args.task_id, args.agent, reason=args.reason)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        if task is None:
            print(f"Task not found: {args.task_id}", file=sys.stderr)
            return 1
        reason_suffix = f" — {args.reason}" if args.reason else ""
        print(f"Rejected: {task.get('title')} ({task.get('id')}){reason_suffix}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
