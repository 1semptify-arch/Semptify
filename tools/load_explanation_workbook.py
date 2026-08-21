#!/usr/bin/env python3
"""Load a context-explanation workbook CSV into context_explanation_entries.

Usage:
    python tools/load_explanation_workbook.py data/explanation_workbook_example.csv
    python tools/load_explanation_workbook.py data/explanation_workbook.csv --dry-run
    python tools/load_explanation_workbook.py data/explanation_workbook.csv --jurisdiction MN

The CSV must have headers:
    subject,jurisdiction,upl_risk_tier,pillar,review_status,
    variant_mechanics,variant_trust,variant_reinforcement,variant_minimal

The script validates each row, creates an embedding, and inserts the entry.
It skips and reports bad rows without stopping the batch.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import sys
from pathlib import Path

# Ensure repo root is on path so app.* imports work.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.modules.context_engine.explanation_entries import (
    PILLAR_NAMES,
    REVIEW_STATUSES,
    UPL_RISK_TIERS,
    create_explanation_entry,
)
from app.modules.context_engine.taxonomy import ALL_SUBJECTS

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "subject",
    "jurisdiction",
    "upl_risk_tier",
    "pillar",
    "review_status",
    "variant_mechanics",
    "variant_trust",
    "variant_reinforcement",
    "variant_minimal",
]

VALID_SUBJECTS = set(ALL_SUBJECTS)
VALID_PILLARS = PILLAR_NAMES
VALID_RISK_TIERS = UPL_RISK_TIERS
VALID_REVIEW_STATUSES = REVIEW_STATUSES


PLACEHOLDER_MARKERS = ("[FILL", "TODO", "[TODO", "[WRITE")


def _row_has_placeholders(row: dict[str, str]) -> list[str]:
    """Return the list of variant columns that still contain workbook placeholders."""
    return [
        col for col in ("variant_mechanics", "variant_trust", "variant_reinforcement", "variant_minimal")
        if any(marker in (row.get(col) or "").strip() for marker in PLACEHOLDER_MARKERS)
    ]


def _validate_row(row: dict[str, str], line_no: int) -> tuple[list[str], list[str]]:
    """Return (errors, placeholder_cols) for the row."""
    errors: list[str] = []

    for col in REQUIRED_COLUMNS:
        cell = (row.get(col) or "").strip()
        if not cell:
            errors.append(f"line {line_no}: missing or empty '{col}'")
            row[col] = cell

    subject = (row.get("subject") or "").strip()
    if subject and subject not in VALID_SUBJECTS:
        errors.append(
            f"line {line_no}: invalid subject '{subject}'. "
            f"Must be one of: {', '.join(sorted(VALID_SUBJECTS))}"
        )

    pillar = (row.get("pillar") or "").strip()
    if pillar and pillar not in VALID_PILLARS:
        errors.append(
            f"line {line_no}: invalid pillar '{pillar}'. "
            f"Must be one of: {', '.join(sorted(VALID_PILLARS))}"
        )

    upl_risk_tier = (row.get("upl_risk_tier") or "").strip()
    if upl_risk_tier and upl_risk_tier not in VALID_RISK_TIERS:
        errors.append(
            f"line {line_no}: invalid upl_risk_tier '{upl_risk_tier}'. "
            f"Must be one of: {', '.join(sorted(VALID_RISK_TIERS))}"
        )

    review_status = (row.get("review_status") or "").strip()
    if review_status and review_status not in VALID_REVIEW_STATUSES:
        errors.append(
            f"line {line_no}: invalid review_status '{review_status}'. "
            f"Must be one of: {', '.join(sorted(VALID_REVIEW_STATUSES))}"
        )

    placeholder_cols = _row_has_placeholders(row)

    # Warn if any variant contains HTML-like tags.
    for col in ("variant_mechanics", "variant_trust", "variant_reinforcement", "variant_minimal"):
        text = (row.get(col) or "").strip()
        if "<" in text and ">" in text:
            errors.append(
                f"line {line_no}: '{col}' appears to contain HTML tags. "
                "Use plain text only."
            )

    return errors, placeholder_cols


async def _load(
    path: Path,
    dry_run: bool,
    default_jurisdiction: str | None,
    show_placeholders: bool,
) -> int:
    rows_read = 0
    created = 0
    skipped = 0
    placeholder_skipped = 0
    placeholder_lines: list[int] = []
    errors: list[str] = []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        # Validate header
        if reader.fieldnames is None:
            print("Error: CSV has no header row.", file=sys.stderr)
            return 1

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing_cols:
            print(
                f"Error: CSV missing required columns: {', '.join(missing_cols)}",
                file=sys.stderr,
            )
            return 1

        for line_no, row in enumerate(reader, start=2):
            rows_read += 1

            # Apply default jurisdiction if the row leaves it blank.
            if default_jurisdiction and (row.get("jurisdiction") or "").strip() == "":
                row["jurisdiction"] = default_jurisdiction

            row_errors, placeholder_cols = _validate_row(row, line_no)

            # Placeholder rows are summarized, not listed, unless requested.
            if placeholder_cols and not row_errors:
                placeholder_skipped += 1
                placeholder_lines.append(line_no)
                if show_placeholders:
                    errors.append(
                        f"line {line_no}: {len(placeholder_cols)} variant(s) still contain placeholders "
                        f"({', '.join(placeholder_cols)}). Replace [FILL... / TODO markers before loading."
                    )
                skipped += 1
                continue

            if row_errors:
                errors.extend(row_errors)
                skipped += 1
                continue

            if dry_run:
                print(
                    f"Would create: "
                    f"{(row.get('subject') or '').strip()} / "
                    f"{(row.get('jurisdiction') or '').strip()} / "
                    f"{(row.get('pillar') or '').strip()}"
                )
                created += 1
                continue

            try:
                entry = await create_explanation_entry(
                    subject=(row.get("subject") or "").strip(),
                    jurisdiction=(row.get("jurisdiction") or "").strip(),
                    upl_risk_tier=(row.get("upl_risk_tier") or "").strip(),
                    pillar=(row.get("pillar") or "").strip(),
                    review_status=(row.get("review_status") or "").strip(),
                    variant_mechanics=(row.get("variant_mechanics") or "").strip(),
                    variant_trust=(row.get("variant_trust") or "").strip(),
                    variant_reinforcement=(row.get("variant_reinforcement") or "").strip(),
                    variant_minimal=(row.get("variant_minimal") or "").strip(),
                )
                print(f"Created {entry.entry_id}: {row['subject']} / {row['jurisdiction']} / {row['pillar']}")
                created += 1
            except Exception as exc:
                logger.exception("line %d: failed to create entry", line_no)
                errors.append(f"line {line_no}: {exc}")
                skipped += 1

    print(f"\nRows read: {rows_read}")
    print(f"Created:   {created}")
    print(f"Skipped:   {skipped}")
    if placeholder_skipped:
        print(
            f"  - {placeholder_skipped} rows skipped because they still contain placeholders. "
            f"Use --show-placeholders to list each line."
        )

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err}")

    return 0 if skipped == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Load context explanation workbook CSV")
    parser.add_argument("csv_path", type=Path, help="Path to the workbook CSV")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not write to DB")
    parser.add_argument("--jurisdiction", default=None, help="Default jurisdiction for blank rows")
    parser.add_argument(
        "--show-placeholders",
        action="store_true",
        help="List every row that still contains a [FILL... / TODO marker",
    )
    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"Error: file not found: {args.csv_path}", file=sys.stderr)
        return 1

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    return asyncio.run(_load(args.csv_path, args.dry_run, args.jurisdiction, args.show_placeholders))


if __name__ == "__main__":
    sys.exit(main())
