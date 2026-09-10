#!/usr/bin/env python3
"""docs_staleness_check.py — regenerate docs/STALENESS-REPORT.md from doc-map.yaml.

Usage:
    .\venv311\\Scripts\\Activate.ps1
    python tools/docs_staleness_check.py [options]

This is the first job of the recurring internal scheduler. It reads
`docs/doc-map.yaml`, compares the most recent git commit touching each covered
code path against the most recent git commit touching the doc file, and flags
docs whose code changed more recently than the doc by at least the threshold.

It also runs the Documentation Reconciliation Pass described in
`docs/orchestration/documentation-staleness-protocol.md`: it checks the three
canonical SSOT docs, sweeps handoff/temp folders, and scans for lightweight,
flag-only contradictions in public-facing copy. Nothing is archived or deleted
automatically — the report is for the designated reviewer.

Output is `docs/STALENESS-REPORT.md`. The script does NOT commit the report —
that is left for the designated reviewer.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
# Semptify repo is at C:\master-repo\modules\app-semptify-fastapi; master superproject is two levels above.
MASTER_ROOT = REPO_ROOT.parent.parent
DOC_MAP_PATH = REPO_ROOT / "docs" / "doc-map.yaml"
REPORT_PATH = REPO_ROOT / "docs" / "STALENESS-REPORT.md"
DEFAULT_THRESHOLD_DAYS = 21

# Canonical SSOT docs required by the Documentation Staleness Protocol.
CANONICAL_DOCS = {
    "NAMING_SSOT_DICTIONARY.md": MASTER_ROOT / "NAMING_SSOT_DICTIONARY.md",
    "SEMPTIFY_REFERENCE_LIBRARY.md": MASTER_ROOT / "SEMPTIFY_REFERENCE_LIBRARY.md",
    "BUILD_STATE.md": REPO_ROOT / "BUILD_STATE.md",
}

# Handoff/temp folders that the recurring reconciliation pass must inspect.
TEMP_FOLDERS = [
    MASTER_ROOT / "hand offs and temp",
    MASTER_ROOT / "New hand offs and zips",
]

# Known risk areas listed in docs/orchestration/documentation-staleness-protocol.md.
# The pass checks whether these still exist so the next reviewer knows where to look.
RISK_AREAS = [
    ("footer parallel implementations", [
        REPO_ROOT / "app/templates/base.html",
        REPO_ROOT / "static/js/unified-footer-loader.js",
        REPO_ROOT / "app/templates/components/footer.html",
    ]),
    ("gap_report.py", [REPO_ROOT / "tools" / "gap_report.py"]),
    ("legacy pages audit", [MASTER_ROOT / "LEGACY_PAGES_AUDIT.md"]),
]


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


def _canonical_doc_status() -> str:
    """Report whether the three canonical SSOT docs exist and are tracked."""
    lines = ["### Canonical SSOT docs", ""]
    for name, path in CANONICAL_DOCS.items():
        if not path.exists():
            lines.append(f"- **{name}**: MISSING at `{path}`")
            continue
        t = _git_last_commit_time(path)
        age = "unknown"
        if t is not None:
            age = t.strftime("%Y-%m-%d")
        lines.append(f"- **{name}**: present, last commit `{age}` (`{path}`)")
    lines.append("")
    return "\n".join(lines)


def _handoff_temp_sweep() -> str:
    """List remaining handoff/temp files; reconciliation is not auto-deletion."""
    lines = ["### Handoff / temp folder sweep", ""]
    for folder in TEMP_FOLDERS:
        if not folder.exists():
            lines.append(f"- `{folder}`: does not exist")
            continue
        entries = [p for p in folder.iterdir()]
        if not entries:
            lines.append(f"- `{folder}`: empty")
        else:
            lines.append(f"- `{folder}`: {len(entries)} item(s)")
            for entry in sorted(entries, key=lambda p: p.name.lower()):
                marker = " (flagged — undetermined)" if entry.is_file() and entry.name != "TEMP_SWEEP_REPORT.md" else ""
                lines.append(f"  - `{entry.name}`{marker}")
    report = MASTER_ROOT / "hand offs and temp" / "TEMP_SWEEP_REPORT.md"
    if report.exists():
        lines.append("")
        lines.append(f"- Sweep report exists: `{report}`")
    lines.append("")
    return "\n".join(lines)


def _ssot_contradiction_scan() -> str:
    """First-pass, flag-only scan for known SSOT language contradictions.

    This is intentionally lightweight. It does not archive or delete anything.
    A human/agent must review each match and decide whether the SSOT or the
    occurrence is the one that is outdated.
    """
    lines = ["### SSOT contradiction scan (flag-only)", ""]

    # Pattern: the word "free" used to describe a Semptify product/offering.
    # We scan only selected public-facing / guidance docs and templates.
    free_pattern = re.compile(r"\bfree\b", re.IGNORECASE)
    scan_targets = [
        REPO_ROOT / "docs" / "user-guides" / "USER_GUIDE.md",
        REPO_ROOT / "app" / "templates" / "index.html",
        REPO_ROOT / "app" / "templates" / "public_base.html",
        MASTER_ROOT / "SEMPTIFY_REFERENCE_LIBRARY.md",
    ]
    free_matches: list[str] = []
    for target in scan_targets:
        if not target.exists():
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except OSError:
            continue
        for i, raw_line in enumerate(text.splitlines(), 1):
            if free_pattern.search(raw_line):
                free_matches.append(f"- `{target.relative_to(MASTER_ROOT if target.is_relative_to(MASTER_ROOT) else REPO_ROOT)}:{i}`: {raw_line.strip()[:120]}")

    if free_matches:
        lines.append("**Matches for 'free' (review whether it describes Semptify itself):**")
        lines.extend(free_matches[:20])
        if len(free_matches) > 20:
            lines.append(f"- ... and {len(free_matches) - 20} more matches")
    else:
        lines.append("- No 'free' matches in scanned targets.")
    lines.append("")

    # Pattern: business-model/account language in public-facing templates.
    login_pattern = re.compile(r"\b(log\s*in|login|sign\s*up|sign-up|account|subscription|premium|pricing|trial)\b", re.IGNORECASE)
    login_matches: list[str] = []
    public_templates_dir = REPO_ROOT / "app" / "templates" / "public"
    if public_templates_dir.exists():
        for target in sorted(public_templates_dir.rglob("*.html")):
            try:
                text = target.read_text(encoding="utf-8")
            except OSError:
                continue
            for i, raw_line in enumerate(text.splitlines(), 1):
                if login_pattern.search(raw_line):
                    login_matches.append(f"- `{target.relative_to(REPO_ROOT)}:{i}`: {raw_line.strip()[:120]}")

    if login_matches:
        lines.append("**Matches for business-model / account language in public templates (review for public-facing copy):**")
        lines.extend(login_matches[:20])
        if len(login_matches) > 20:
            lines.append(f"- ... and {len(login_matches) - 20} more matches")
    else:
        lines.append("- No account/login/pricing language matches in public templates.")
    lines.append("")
    return "\n".join(lines)


def _known_risk_area_check() -> str:
    """Surface whether the risk areas named in the Staleness Protocol are still present."""
    lines = ["### Known risk area check", ""]
    for label, paths in RISK_AREAS:
        present = [str(p.relative_to(REPO_ROOT if p.is_relative_to(REPO_ROOT) else MASTER_ROOT)) for p in paths if p.exists()]
        missing = [str(p) for p in paths if not p.exists()]
        if present:
            lines.append(f"- **{label}**: still present — {', '.join(present)}")
        if missing:
            lines.append(f"- **{label}**: not found — {', '.join(missing)}")
    lines.append("")
    return "\n".join(lines)


def _reconciliation_report() -> str:
    """Assemble the Documentation Reconciliation Pass section."""
    sections = [
        "## Documentation Reconciliation Pass",
        "",
        "This section is generated by the recurring `docs-staleness` job. It does not",
        "auto-archive or auto-delete; it flags candidate contradictions and stale temp",
        "files so the next reviewer can decide, per the Staleness Protocol.",
        "",
        _canonical_doc_status(),
        _handoff_temp_sweep(),
        _ssot_contradiction_scan(),
        _known_risk_area_check(),
    ]
    return "\n".join(sections)


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
    lines.append(_reconciliation_report())
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
