#!/usr/bin/env python3
"""
Generate a CSV inventory of module/router/service compliance entries using
`app.core.compliance` discovery. Run from repository root.
"""
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.compliance import MODULE_COMPLIANCE_INVENTORY


def category_of(path: str) -> str:
    if path.startswith("app/modules/"):
        return "module"
    if "/routers/" in path or path.startswith("app/routers/"):
        return "router"
    if "/services/" in path or path.startswith("app/services/"):
        return "service"
    return "other"


def main() -> None:
    out = ROOT / "MODULE_COMPLIANCE_INVENTORY.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "category",
            "name",
            "file_path",
            "status",
            "privacy_scope",
            "evidence_role",
            "security_notes",
            "next_action",
        ])

        for m in MODULE_COMPLIANCE_INVENTORY:
            writer.writerow([
                category_of(m.file_path),
                m.name,
                m.file_path,
                m.status,
                m.privacy_scope,
                m.evidence_role,
                m.security_notes,
                m.next_action,
            ])

    print(f"Wrote inventory to {out}")


if __name__ == "__main__":
    main()
