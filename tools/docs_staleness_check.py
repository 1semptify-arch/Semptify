#!/usr/bin/env python3
"""docs_staleness_check.py — regenerate docs/STALENESS-REPORT.md from doc-map.yaml.

Usage:
    .\venv311\\Scripts\\Activate.ps1
    python tools/docs_staleness_check.py [options]

This is the first job of the recurring internal scheduler. It reads
`docs/doc-map.yaml`, compares the most recent git commit touching each covered
code path against the most recent git commit touching the doc file, and flags
docs whose code changed more recently than the doc by at least the threshold.

Output is `docs/STALENESS-REPORT.md`. The script does NOT commit the report —
that is left for the designated reviewer.
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_MAP_PATH = REPO_ROOT / "docs" / "doc-map.yaml"
REPORT_PATH = REPO_ROOT / "docs" / "STALENESS-REPORT.md"
DEFAULT_THRESHOLD_DAYS = 21


def _git_last_commit_time(path: Path) -> datetime.datetime | None:
    """Return the datetime of the most recent commit touching `path`.

    Uses `git log -1` which works on files and directories. Returns `None`
    when the path is not tracked by git (e.g. untracked files).
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    iso = result.stdout.strip().splitlines()[0]
    return datetime.datetime.fromisoformat(iso)


def _load_doc_map() -> list[dict]:
    return yaml.safe_load(DOC_MAP_PATH.read_text(encoding="utf-8")) or []


def _compute_staleness(threshold_days: int) -> list[dict]:
    entries = _load_doc_map()
    threshold = datetime.timedelta(days=threshold_days)
    datetime.datetime.now(tz=datetime.UTC)
    flagged = []

    for entry in entries:
        doc_file = REPO_ROOT / "docs" / entry["doc"]
        doc_time = _git_last_commit_time(doc_file)

        latest_code_time: datetime.datetime | None = None
        latest_cover: str | None = None
        for cover in entry.get("covers", []):
            cover_path = REPO_ROOT / cover
            if not cover_path.exists():
                continue
            t = _git_last_commit_time(cover_path)
            if t is not None and (latest_code_time is None or t > latest_code_time):
                latest_code_time = t
                latest_cover = cover

        if doc_time is None or latest_code_time is None:
            # Missing history for one side — cannot compare. Flag as needing review.
            flagged.append(
                {
                    "doc": entry["doc"],
                    "category": entry["category"],
                    "doc_time": doc_time,
                    "code_time": latest_code_time,
                    "gap_days": None,
                    "cover": latest_cover,
                    "reason": (
                        "missing git history"
                        if doc_time is None and latest_code_time is None
                        else ("doc has no git history" if doc_time is None else "covered code has no git history")
                    ),
                }
            )
            continue

        gap = latest_code_time - doc_time
        if gap >= threshold and latest_code_time > doc_time:
            flagged.append(
                {
                    "doc": entry["doc"],
                    "category": entry["category"],
                    "doc_time": doc_time,
                    "code_time": latest_code_time,
                    "gap_days": gap.days,
                    "cover": latest_cover,
                    "reason": f"code changed {gap.days} days after doc",
                }
            )

    # Sort by category, then by descending gap, then by doc name.
    flagged.sort(key=lambda x: (x["category"], -(x["gap_days"] or 0), x["doc"]))
    return flagged


def _format_time(t: datetime.datetime | None) -> str:
    if t is None:
        return "unknown"
    return t.strftime("%Y-%m-%d")


def _generate_report(flagged: list[dict], threshold_days: int) -> str:
    now = datetime.datetime.now(tz=datetime.UTC)
    total = len(flagged)

    lines = [
        "# Documentation Staleness Report",
        "",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Threshold: {threshold_days} days",
        f"Flagged entries: {total}",
        "",
        "This report is regenerated each run. It does not auto-update docs.",
        "A human or designated agent reviews each item and decides what to update.",
        "",
        "## Summary by category",
        "",
    ]

    by_category: dict[str, int] = {}
    for f in flagged:
        by_category[f["category"]] = by_category.get(f["category"], 0) + 1

    if by_category:
        for cat, count in sorted(by_category.items()):
            lines.append(f"- {cat}: {count}")
    else:
        lines.append("- None")

    lines.extend(["", "## Flagged docs", ""])

    if not flagged:
        lines.append("No docs are stale. Nothing to review.")
        lines.append("")
        return "\n".join(lines)

    current_cat = None
    for f in flagged:
        if f["category"] != current_cat:
            current_cat = f["category"]
            lines.append(f"### {current_cat}")
            lines.append("")

        gap = f"{f['gap_days']} days" if f["gap_days"] is not None else f["reason"]
        latest = f["cover"] or "any covered path"
        lines.append(f"- **{f['doc']}**")
        lines.append(f"  - Latest code change: {_format_time(f['code_time'])} (`{latest}`)")
        lines.append(f"  - Latest doc change: {_format_time(f['doc_time'])}")
        lines.append(f"  - Gap: {gap}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("Run `python tools/docs_staleness_check.py` to regenerate this report.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate docs/STALENESS-REPORT.md from doc-map.yaml.")
    parser.add_argument(
        "--threshold-days",
        type=int,
        default=DEFAULT_THRESHOLD_DAYS,
        help=f"Days between code and doc change before flagging (default: {DEFAULT_THRESHOLD_DAYS}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPORT_PATH,
        help=f"Output path for the report (default: {REPORT_PATH}).",
    )
    args = parser.parse_args()

    flagged = _compute_staleness(args.threshold_days)
    report = _generate_report(flagged, args.threshold_days)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output} - {len(flagged)} docs flagged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
