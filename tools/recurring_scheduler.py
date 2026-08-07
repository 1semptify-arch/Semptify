#!/usr/bin/env python3
"""recurring_scheduler.py — lightweight dispatcher for recurring agent review jobs.

Usage:
    .\venv311\\Scripts\\Activate.ps1
    python tools/recurring_scheduler.py --run-all
    python tools/recurring_scheduler.py --run docs-staleness
    python tools/recurring_scheduler.py --list

This is standing infrastructure for any task that needs regular evaluation and
human review. Jobs are defined in the JOBS registry below. Each job is a module
path + function that returns an int exit code. The scheduler records the last
run time in `tools/.recurring_scheduler_state.json` so `--run-due` only runs
jobs whose cadence has elapsed.

Current jobs:
    docs-staleness   — weekly docs staleness check (regenerates docs/STALENESS-REPORT.md)
    docs-changelog   — weekly categorized changelog update (appends to docs/CHANGELOG-*.md)
    ocr-beta-review  — TBD placeholder for monitoring ADR 0007 beta metrics

Intended cadences:
    docs-staleness:  7 days
    docs-changelog:  7 days
    ocr-beta-review: 7 days (once metrics are wired)

Do NOT run this as a daemon. Use cron, CI, or a Windows scheduled task.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "tools" / ".recurring_scheduler_state.json"


def _run_python(script_path: str) -> int:
    """Run a Python script under the project venv (Windows path).

    Output is not re-printed to avoid terminal encoding issues. Child scripts
    are responsible for their own output files (e.g. docs/STALENESS-REPORT.md).
    """
    python = REPO_ROOT / "venv311" / "Scripts" / "python.exe"
    return subprocess.run(
        [str(python), script_path],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode


def _ocr_beta_review_placeholder() -> int:
    print("ocr-beta-review: metrics not yet wired. Add to this function once client-side")
    print("OCR accuracy, fallback rate, and classification confidence are available.")
    return 0


JOBS: dict[str, dict[str, object]] = {
    "docs-staleness": {
        "cadence_days": 7,
        "fn": lambda: _run_python("tools/docs_staleness_check.py"),
        "description": "Regenerate docs/STALENESS-REPORT.md",
    },
    "docs-changelog": {
        "cadence_days": 7,
        "fn": lambda: _run_python("tools/docs_changelog.py"),
        "description": "Append categorized commit log to docs/CHANGELOG-*.md",
    },
    "ocr-beta-review": {
        "cadence_days": 7,
        "fn": _ocr_beta_review_placeholder,
        "description": "Placeholder for monitoring ADR 0007 beta metrics",
    },
}


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _is_due(state: dict, name: str, cadence_days: int) -> bool:
    last_str = state.get(name)
    if not last_str:
        return True
    last = datetime.datetime.fromisoformat(last_str)
    now = datetime.datetime.now(tz=datetime.UTC)
    return (now - last) >= datetime.timedelta(days=cadence_days)


def _run_job(name: str, dry_run: bool = False) -> int:
    spec = JOBS.get(name)
    if not spec:
        print(f"Unknown job: {name}")
        return 1

    print(f"Running job: {name} - {spec['description']}")
    if dry_run:
        print("(dry run)")
        return 0

    fn = spec["fn"]
    return fn()


def _list_jobs() -> None:
    state = _load_state()
    datetime.datetime.now(tz=datetime.UTC)
    print("Registered jobs:")
    for name, spec in JOBS.items():
        last = state.get(name, "never")
        due = (
            "now"
            if last == "never"
            else (datetime.datetime.fromisoformat(last) + datetime.timedelta(days=spec["cadence_days"])).strftime(
                "%Y-%m-%d %H:%M"
            )
        )
        print(f"  {name}: cadence {spec['cadence_days']}d, last run {last}, due {due}")
        print(f"    {spec['description']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatcher for recurring agent review jobs.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", help="Run a single job by name.")
    group.add_argument("--run-all", action="store_true", help="Run every registered job.")
    group.add_argument("--run-due", action="store_true", help="Run only jobs whose cadence has elapsed.")
    group.add_argument("--list", action="store_true", help="List jobs and due dates.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would run, without running.")
    args = parser.parse_args()

    if args.list:
        _list_jobs()
        return 0

    state = _load_state()
    now = datetime.datetime.now(tz=datetime.UTC).isoformat()

    if args.run:
        code = _run_job(args.run, dry_run=args.dry_run)
        if code == 0 and not args.dry_run:
            state[args.run] = now
            _save_state(state)
        return code

    jobs_to_run = (
        list(JOBS.keys())
        if args.run_all
        else [name for name, spec in JOBS.items() if _is_due(state, name, spec["cadence_days"])]
    )

    overall = 0
    for name in jobs_to_run:
        code = _run_job(name, dry_run=args.dry_run)
        overall = max(overall, code)
        if code == 0 and not args.dry_run:
            state[name] = now

    if not args.dry_run:
        _save_state(state)

    if not jobs_to_run:
        print("No jobs due.")
    return overall


if __name__ == "__main__":
    raise SystemExit(main())
