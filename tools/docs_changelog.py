#!/usr/bin/env python3
"""docs_changelog.py — append categorized commit summaries to docs/CHANGELOG-{category}.md.

Usage:
    .\venv311\Scripts\Activate.ps1
    python tools/docs_changelog.py [options]

Reads `docs/doc-map.yaml` to know which code paths and docs belong to each
category. Parses recent git commits and, for any commit whose message starts
with `admin:`, `user:`, `help:`, or `adr:` and whose touched files overlap with
a doc-map category, appends a line to `docs/CHANGELOG-{category}.md`:

    - YYYY-MM-DD HH:MM [hash] short description | files touched

By default it processes commits since the last line already in the changelog,
so it is safe to run repeatedly. Run it from a scheduler (e.g. weekly) or as a
post-merge/post-push step.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_MAP_PATH = REPO_ROOT / "docs" / "doc-map.yaml"
CHANGELOG_DIR = REPO_ROOT / "docs"
CATEGORIES = ("admin", "user", "help", "adr")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _load_doc_map() -> list[dict]:
    return yaml.safe_load(DOC_MAP_PATH.read_text(encoding="utf-8")) or []


def _category_paths(doc_map: list[dict]) -> dict[str, set[str]]:
    """Return a mapping from category to the set of repo-relative paths it covers."""
    mapping: dict[str, set[str]] = {cat: set() for cat in CATEGORIES}
    for entry in doc_map:
        cat = entry.get("category", "admin")
        if cat not in mapping:
            cat = "admin"
        # The doc itself is also part of the category's surface area.
        mapping[cat].add(Path("docs") / entry["doc"])
        for cover in entry.get("covers", []):
            mapping[cat].add(Path(cover))
    return mapping


def _match_category(
    category_paths: dict[str, set[str]], touched_files: set[str]
) -> set[str]:
    """Return which categories have any path overlap with touched files."""
    matched: set[str] = set()
    touched = {Path(f) for f in touched_files}
    for cat, paths in category_paths.items():
        for t in touched:
            if any(p == t or t in p.parents or p in t.parents for p in paths):
                matched.add(cat)
                break
    return matched


def _latest_logged_dates() -> dict[str, datetime.datetime]:
    dates: dict[str, datetime.datetime] = {}
    for cat in CATEGORIES:
        path = CHANGELOG_DIR / f"CHANGELOG-{cat}.md"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ", line)
            if m:
                dt = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
                dt = dt.replace(tzinfo=datetime.timezone.utc)
                if cat not in dates or dt > dates[cat]:
                    dates[cat] = dt
    return dates


def _get_commits(since: datetime.datetime | None = None) -> list[dict]:
    """Return list of commits with hash, date, message, and files."""
    fmt = "%H%x00%cI%x00%s%x00"
    args = ["log", f"--format={fmt}", "--name-only", "--no-renames"]
    if since is not None:
        # git log --since requires an ISO string; include equality for the exact second.
        args.extend(["--since", since.strftime("%Y-%m-%dT%H:%M:%S%z")])
    output = _git(*args)

    commits: list[dict] = []
    blocks = output.split("\n\n")
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln]
        if not lines:
            continue
        parts = lines[0].split("\x00")
        if len(parts) < 3:
            continue
        commit_hash, iso, subject = parts[0], parts[1], parts[2]
        files = set(lines[1:])
        commits.append(
            {
                "hash": commit_hash[:12],
                "date": datetime.datetime.fromisoformat(iso),
                "subject": subject,
                "files": set(lines[1:]),
            }
        )
    return commits


def _parse_category_prefix(subject: str) -> tuple[str | None, str]:
    """Return (category, rest_of_subject) if the subject starts with a known prefix."""
    for cat in CATEGORIES:
        if subject.startswith(f"{cat}:"):
            return cat, subject[len(f"{cat}:"):].strip()
    return None, subject


def _append_to_changelog(cat: str, lines: list[str]) -> None:
    path = CHANGELOG_DIR / f"CHANGELOG-{cat}.md"
    header = f"# {cat.capitalize()} Changelog\n\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if not existing.startswith(header.strip()):
            existing = header + existing
    else:
        existing = header

    new_content = existing.rstrip("\n") + "\n" + "\n".join(lines) + "\n"
    path.write_text(new_content, encoding="utf-8")


def _format_entry(commit: dict, cleaned_subject: str, files: list[str]) -> str:
    date_str = commit["date"].astimezone(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M"
    )
    file_list = ", ".join(sorted(files))[:120]
    if len(", ".join(sorted(files))) > 120:
        file_list += "…"
    return f"- {date_str} [{commit['hash']}] {cleaned_subject} | {file_list}"


def _relevant_files_for_category(
    cat: str, commit_files: set[str], category_paths: dict[str, set[str]]
) -> list[str]:
    matched: set[str] = set()
    for f in commit_files:
        fp = Path(f)
        for p in category_paths.get(cat, set()):
            if fp == p or fp in p.parents or p in fp.parents:
                matched.add(str(fp))
    return sorted(matched)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append categorized commit summaries to docs/CHANGELOG-{category}.md."
    )
    parser.add_argument(
        "--since",
        help="Process commits since this ISO datetime (default: since last changelog entry).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all commits, not just those since the last changelog entry.",
    )
    args = parser.parse_args()

    doc_map = _load_doc_map()
    category_paths = _category_paths(doc_map)

    if args.all:
        since = None
    elif args.since:
        since = datetime.datetime.fromisoformat(args.since)
    else:
        since = max(_latest_logged_dates().values(), default=None)

    commits = _get_commits(since)
    added: dict[str, list[str]] = {cat: [] for cat in CATEGORIES}

    for commit in commits:
        prefix, cleaned = _parse_category_prefix(commit["subject"])
        if not prefix:
            continue

        # The commit message explicitly carries a category; we only log it if it
        # actually touched something this category cares about.
        matched_cats = _match_category(category_paths, commit["files"])
        if prefix not in matched_cats:
            # If a commit has an explicit prefix but the touched files don't map,
            # still record it under that prefix — the author chose the category.
            matched_cats = {prefix}

        for cat in matched_cats:
            files = _relevant_files_for_category(cat, commit["files"], category_paths)
            added[cat].append(_format_entry(commit, cleaned, files))

    for cat, lines in added.items():
        if lines:
            _append_to_changelog(cat, lines)
            print(f"CHANGELOG-{cat}.md: +{len(lines)} entries")

    total = sum(len(v) for v in added.values())
    print(
        f"Appended {total} changelog entries across "
        f"{len([v for v in added.values() if v])} categories."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
