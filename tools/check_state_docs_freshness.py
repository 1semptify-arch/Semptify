#!/usr/bin/env python3
"""check_state_docs_freshness.py — soft warning when tracker status changes outrun state docs.

This is a lightweight report, not a hard CI gate. It looks at the recent git
history and flags commits where a significant number of tracker tasks flip to
`resolved` without a corresponding touch to `BUILD_STATE.md` or
`ACTIVE_CONTEXT.md` nearby in the same window of commits.

Usage:
    python tools/check_state_docs_freshness.py              # soft report, exits 0
    python tools/check_state_docs_freshness.py --strict     # exits 1 if warnings

Run `sync_orchestrator.py --check` after any tracker-touching change.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DOCS = ("BUILD_STATE.md", "ACTIVE_CONTEXT.md")
TRACKER_FILES = ("tools/agent_orchestrator_tasks.json", "tools/_seed_orchestrator_tasks.py")


def git_run(args: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def get_recent_commits(n: int) -> list[dict]:
    result = git_run(["log", f"-n{n}", "--format=%H %ct %s"])
    commits: list[dict] = []
    for line in result.stdout.splitlines():
        parts = line.split(" ", 2)
        if len(parts) >= 2:
            commits.append({
                "hash": parts[0],
                "time": int(parts[1]),
                "subject": parts[2] if len(parts) == 3 else "",
            })
    return commits


def files_in_commit(commit_hash: str) -> set[str]:
    result = git_run(["diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash])
    return {name for name in result.stdout.splitlines() if name}


def read_file_at_rev(rev: str, path: str) -> str | None:
    result = git_run(["show", f"{rev}:{path}"])
    if result.returncode != 0:
        return None
    return result.stdout


def parse_tracker(text: str, path: str) -> list[dict] | None:
    if not text:
        return None
    if path.endswith(".json"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, list) else None
    if path.endswith(".py"):
        match = re.search(r"TASKS\s*=\s*(\[.*?\n\])", text, re.DOTALL)
        if not match:
            return None
        try:
            return ast.literal_eval(match.group(1))
        except (ValueError, SyntaxError):
            return None
    return None


def count_resolved_changes(parent: list[dict] | None, current: list[dict] | None) -> int:
    if not isinstance(parent, list):
        parent = []
    if not isinstance(current, list):
        current = []

    parent_by_id: dict[str, dict] = {
        t["id"]: t for t in parent if isinstance(t, dict) and t.get("id")
    }
    current_by_id = {
        t["id"]: t for t in current if isinstance(t, dict) and t.get("id")
    }

    resolved = 0
    for task_id, task in current_by_id.items():
        if task.get("status") != "resolved":
            continue
        prev = parent_by_id.get(task_id)
        if prev is None or prev.get("status") != "resolved":
            resolved += 1
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commits",
        type=int,
        default=30,
        help="Number of recent commits to scan (default: 30).",
    )
    parser.add_argument(
        "--min-resolved",
        type=int,
        default=3,
        help="Minimum tracker tasks resolved in a single commit to be considered significant (default: 3).",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=5,
        help="Number of newer commits (including the same commit) to look for a state-doc update (default: 5).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any warning is produced. Default is a soft warning that exits 0.",
    )
    args = parser.parse_args()

    commits = get_recent_commits(args.commits)
    if not commits:
        print("OK: no commits found.")
        return 0

    changed_files = [files_in_commit(c["hash"]) for c in commits]

    significant: list[tuple[int, dict, int]] = []
    for index, commit in enumerate(commits):
        total_resolved = 0
        for tracker in TRACKER_FILES:
            current_text = read_file_at_rev(commit["hash"], tracker)
            current = parse_tracker(current_text, tracker) if current_text else None
            parent_text = read_file_at_rev(f"{commit['hash']}^", tracker)
            parent = parse_tracker(parent_text, tracker) if parent_text else None
            total_resolved += count_resolved_changes(parent, current)

        if total_resolved >= args.min_resolved:
            significant.append((index, commit, total_resolved))

    flagged: list[tuple[int, dict, int]] = []
    for index, commit, resolved_count in significant:
        # Check the same commit and the `window` newer commits (lower index).
        found = False
        for j in range(max(0, index - args.window), index + 1):
            if changed_files[j].intersection(STATE_DOCS):
                found = True
                break
        if not found:
            flagged.append((index, commit, resolved_count))

    if not flagged:
        print(
            "OK: no significant tracker status changes are missing a nearby state-doc update."
        )
        return 0

    print(
        f"WARNING: {len(flagged)} significant tracker status change(s) had no nearby "
        f"BUILD_STATE.md or ACTIVE_CONTEXT.md update."
    )
    for index, commit, resolved_count in flagged:
        when = datetime.fromtimestamp(commit["time"], tz=UTC).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        print(
            f"  - {commit['hash'][:8]} ({when}) — {resolved_count} task(s) resolved; "
            f"no state-doc touch within {args.window} commit(s)"
        )
    print(
        "\nThis is a soft warning. Update the relevant state doc(s) before closing the "
        "session, then run this check again."
    )
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
