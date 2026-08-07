#!/usr/bin/env python3
"""check_commit_msg.py — commit-msg hook for Semptify doc categories.

Usage (from a git commit-msg hook):
    python tools/hooks/check_commit_msg.py <commit-msg-file>

If the commit touches any path covered by docs/doc-map.yaml (either a doc
file itself or a code path in a doc's `covers` list), the commit message
subject must start with one of:

    admin:  user:  help:  adr:

Commits that do not touch mapped docs are allowed with any message.
This is what makes docs_changelog.py useful — the log is split by category.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOC_MAP_PATH = REPO_ROOT / "docs" / "doc-map.yaml"


def _load_doc_map() -> list[dict]:
    return yaml.safe_load(DOC_MAP_PATH.read_text(encoding="utf-8")) or []


def _staged_files() -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return set()
    return set(result.stdout.splitlines())


def _is_under(path: Path, candidate: str) -> bool:
    """Return True if `candidate` equals or is inside `path`.

    Works for both files and directories.
    """
    cand = Path(candidate)
    if path == cand:
        return True
    # is_relative_to is Python 3.9+; repo target is 3.11.9 so this is safe.
    return cand.is_relative_to(path)


def _doc_path_category(p: Path) -> str:
    """Infer a likely changelog category from a path under docs/."""
    parts = p.parts
    if len(parts) > 1 and parts[0] == "docs":
        if len(parts) > 2:
            return parts[1].split("-")[0]  # user-guides -> user, etc.
    return "admin"


def _touches_mapped(staged: set[str], doc_map: list[dict]) -> set[str]:
    """Return the set of matched categories (admin/user/help/adr) for staged files."""
    matched: set[str] = set()
    # staged paths are already relative to repo root from `git diff --cached --name-only`
    staged_paths = {Path(f) for f in staged}

    # Any change inside docs/ likely needs a category prefix.
    for p in staged_paths:
        if p.parts[:1] == ("docs",):
            matched.add(_doc_path_category(p))

    for entry in doc_map:
        category = entry.get("category", "admin")
        # Check the doc file itself.
        doc_path = Path("docs") / entry["doc"]
        for p in staged_paths:
            if _is_under(doc_path, str(p)):
                matched.add(category)
        # Check covered code paths.
        for cover in entry.get("covers", []):
            cover_path = Path(cover)
            for p in staged_paths:
                if _is_under(cover_path, str(p)):
                    matched.add(category)
    return matched


def _category_from_message(subject: str) -> str | None:
    for cat in ("admin", "user", "help", "adr"):
        if subject.lower().startswith(f"{cat}:"):
            return cat
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate commit message category prefix against doc-map.yaml."
    )
    parser.add_argument("msg_file", help="Path to the commit message file.")
    args = parser.parse_args()

    subject = ""
    try:
        with open(args.msg_file, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if line and not line.startswith("#"):
                    subject = line
                    break
    except OSError:
        pass

    staged = _staged_files()
    if not staged:
        # Nothing to check (e.g. amend with no changes).
        return 0

    doc_map = _load_doc_map()
    matched = _touches_mapped(staged, doc_map)

    if not matched:
        # Commit does not touch any mapped doc or code.
        return 0

    category = _category_from_message(subject)
    if not category:
        print("Error: this commit touches documentation/code mapped in docs/doc-map.yaml.", file=sys.stderr)
        print("The commit message subject must start with one of: admin:  user:  help:  adr:", file=sys.stderr)
        print("", file=sys.stderr)
        print("Matched categories:", ", ".join(sorted(matched)), file=sys.stderr)
        print("Subject was:", subject or "<empty>", file=sys.stderr)
        return 1

    if category not in matched:
        print(f"Warning: commit starts with '{category}:' but touches categories: {', '.join(sorted(matched))}.", file=sys.stderr)
        print("Use the most specific category, or split into smaller commits.", file=sys.stderr)
        # Non-fatal: user might have a good reason. The changelog will use the prefix.

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
