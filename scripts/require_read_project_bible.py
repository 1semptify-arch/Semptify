#!/usr/bin/env python3
"""Require project Bible reading before working on Semptify.

This helper is intended as a manual gate for humans and AI assistants.
It prints the canonical document references, then asks for an explicit
confirmation phrase before allowing progress.

Usage:
    python scripts/require_read_project_bible.py

If the acknowledgement is accepted, a local marker file is created:
    .semptify_read_ack

This makes the check idempotent for the current workspace.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

REQUIRED_DOCS = ["PROJECT_BIBLE.md", "README.md", "AGENTS.md"]
ACK_FILE = Path(".semptify_read_ack")
CONFIRMATION_PHRASE = (
    "I have read PROJECT_BIBLE.md, README.md, and AGENTS.md and will use them as the canonical guides."
)


def print_header() -> None:
    print("\n=== Semptify Canonical Readme Enforcement ===\n")
    print("This script is a gate: please read the project-level guidance before working on Semptify.")
    print("It does not stop a determined program, but it does make explicit the team-wide rule.")
    print("\nRequired canonical files:")
    for doc in REQUIRED_DOCS:
        print(f"  - {doc}")
    print("")


def check_docs_exist() -> bool:
    missing = [doc for doc in REQUIRED_DOCS if not Path(doc).exists()]
    if missing:
        print("ERROR: Required canonical docs are missing:")
        for doc in missing:
            print(f"  - {doc}")
        print("Please restore these files before proceeding.")
        return False
    return True


def show_doc_summaries(lines: int = 20) -> None:
    for doc in REQUIRED_DOCS:
        path = Path(doc)
        print(f"\n--- {doc} ---")
        try:
            with path.open("r", encoding="utf-8") as f:
                for _ in range(lines):
                    line = f.readline()
                    if not line:
                        break
                    print(line.rstrip())
        except Exception as exc:
            print(f"Unable to read {doc}: {exc}")


def write_acknowledgement() -> None:
    ACK_FILE.write_text(
        f"ACKNOWLEDGED {datetime.utcnow().isoformat()}Z\n"
        f"Canonical files read: {', '.join(REQUIRED_DOCS)}\n",
        encoding="utf-8",
    )
    print(f"\nAcknowledgement recorded in {ACK_FILE.absolute()}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Require Semptify canonical docs to be read before work begins."
    )
    parser.add_argument(
        "--show-only",
        action="store_true",
        help="Print the canonical doc summaries without prompting for confirmation.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the acknowledgement prompt and only check that required docs exist.",
    )
    args = parser.parse_args()

    if not check_docs_exist():
        return 1

    print_header()

    if ACK_FILE.exists() and not args.force:
        print(f"Found existing acknowledgement marker: {ACK_FILE.name}")
        print("You may proceed.")
        return 0

    show_doc_summaries()

    if args.show_only:
        print("\nRun without --show-only to confirm that you have read these files.")
        return 0

    if args.force:
        print("\nForce mode enabled: required docs exist, but confirmation was skipped.")
        return 0

    print("\nTo continue, type the exact confirmation phrase below and press Enter:")
    print(f"\n{CONFIRMATION_PHRASE}\n")
    response = input("Confirmation: ").strip()

    if response != CONFIRMATION_PHRASE:
        print("\nConfirmation phrase did not match. Aborting.")
        print("Please read the required files and try again.")
        return 2

    write_acknowledgement()
    print("\nThank you. You may now continue working on Semptify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
