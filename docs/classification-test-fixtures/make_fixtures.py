#!/usr/bin/env python3
"""Generate and label deterministic classification test fixtures.

Run this whenever fixture text or layout needs to change. The real-world
failure PDF (lese.pdf) is copied as lease_02.pdf; the other fixtures are
synthetic, generic, and contain no PII.
"""

import json
import shutil
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

FIXTURES_DIR = Path(__file__).resolve().parent
SOURCE_LEASE = Path(r"E:\LEXINGTON FLATS\Leases\lese.pdf")

LEASE_01_TEXT = """\
RESIDENTIAL LEASE AGREEMENT

This Lease Agreement ("Agreement") is made this day between Landlord and Tenant.
The Landlord agrees to rent to the Tenant the premises located at the property
address set forth above. The term of this lease shall commence on the first day
of January, 2025 and shall expire on the thirty-first day of December, 2025.
The monthly rent shall be $1,250.00, due on the first day of each month.
The Tenant has paid a security deposit in the amount of $1,000.00.
IN WITNESS WHEREOF, the parties have signed this lease.
"""

NOTICE_01_TEXT = """\
NOTICE TO QUIT

To: Tenant
From: Landlord

You are hereby notified to vacate the premises within fourteen (14) days.
Your tenancy is terminated. Failure to quit and deliver possession will result
in an unlawful detainer action. This notice is served on this date.
"""

MIXED_01_TEXT = """\
LEASE AND NOTICE TO QUIT (BUNDLED)

RESIDENTIAL LEASE AGREEMENT
This Lease Agreement is made between Landlord and Tenant. The term of this lease
shall commence on January 1, 2025 and expire on December 31, 2025. Monthly rent
is $1,100.00, due on the first of each month. Security deposit is $900.00.

NOTICE TO QUIT
The Landlord hereby gives notice to the Tenant to vacate the premises within
fourteen (14) days. Failure to vacate and deliver possession will result in an
unlawful detainer action.
"""


def _pdf_from_text(text: str, path: Path) -> None:
    """Create a simple, text-only one-page PDF."""
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    x, y = 72, height - 72
    for line in text.splitlines():
        if y < 72:
            c.showPage()
            y = height - 72
        c.drawString(x, y, line)
        y -= 14
    c.save()


def _write_label(filename: str, label: dict) -> None:
    (FIXTURES_DIR / f"{filename}.label.json").write_text(
        json.dumps(label, indent=2), encoding="utf-8"
    )


def main() -> None:
    _pdf_from_text(LEASE_01_TEXT, FIXTURES_DIR / "lease_01.pdf")
    _write_label("lease_01", {
        "type": "lease",
        "notes": "Synthetic generic residential lease with term, rent, deposit, signature markers.",
    })

    _pdf_from_text(NOTICE_01_TEXT, FIXTURES_DIR / "notice_01.pdf")
    _write_label("notice_01", {
        "type": "eviction_notice",
        "notes": "Synthetic generic notice to quit / eviction notice.",
    })

    _pdf_from_text(MIXED_01_TEXT, FIXTURES_DIR / "mixed_01.pdf")
    _write_label("mixed_01", {
        "type": "mixed_document",
        "notes": "Synthetic bundle containing a full lease clause followed by a notice to quit.",
    })

    if SOURCE_LEASE.exists():
        shutil.copy(SOURCE_LEASE, FIXTURES_DIR / "lease_02.pdf")
        _write_label("lease_02", {
            "type": "lease",
            "notes": "Brad's court-admitted lease copy (lese.pdf). Confirmed real-world failure case for Pass 1: dense notice/termination language caused misclassification as eviction_notice.",
        })
    else:
        print(f"Warning: source lease not found at {SOURCE_LEASE}; skipping lease_02 fixture.", file=sys.stderr)

    print("Fixtures generated/updated.")


if __name__ == "__main__":
    main()
