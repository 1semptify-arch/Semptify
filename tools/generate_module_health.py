"""
Bulk generator for module health checks and test suites.

Creates:
  - tests/module_health/test_<id>.py  (one per module)
  - updates tools/module_registry.yaml health_check / test_suite fields

Modules that are ON HOLD, optional-but-missing, or fail import for a required
module are flagged with a ``flag_reason`` and left with ``health_check: TODO``.
"""

from __future__ import annotations

import argparse
import importlib
import shutil
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
REGISTRY_PATH = TOOLS_DIR / "module_registry.yaml"
TEST_DIR = REPO_ROOT / "tests" / "module_health"

# Modules explicitly out of scope for this pass (per Brad's standing direction).
OUT_OF_SCOPE = {
    "vault_sync": "ON HOLD per Brad's standing direction",
    "housing_accountability_accountability_router": "pending Brad's decision on accountability_ledger / detect_repeated_fees",
    "filedored": "pending Brad's decision on filedored_service classification",
}

TEST_TEMPLATE = '''\
"""Auto-generated regression test for {module_id}."""
from tools.module_health import check_{safe_id}


def test_{safe_id}():
    """Verify {module_id} imports, has routes, and has no exposure issues."""
    ok, msg = check_{safe_id}()
    assert ok, msg
'''


def load_registry() -> list[dict]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def save_registry(entries: list[dict]) -> None:
    with REGISTRY_PATH.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(entries, f, sort_keys=False)


def safe_id(module_id: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in module_id).lower()


def can_import(module_path: str) -> bool:
    """Try to import a module without side effects."""
    try:
        importlib.import_module(module_path)
        return True
    except Exception:
        return False


def classify(entry: dict) -> tuple[str, str | None]:
    """Return (health_check_dotted, test_suite_path) or (None, flag_reason)."""
    module_id = entry["id"]
    module_path = entry.get("module_path")

    if module_id in OUT_OF_SCOPE:
        return None, OUT_OF_SCOPE[module_id]

    if not module_path:
        return None, "no module_path"

    # Validate that the module really exists before generating a check.
    if not can_import(module_path):
        # If the product manifest marks it optional, flag it as missing.
        # Otherwise flag it as broken/unresolvable.
        from app.core.product_manifest import MANIFEST

        manifest_entry = MANIFEST.find(module_path)
        if manifest_entry and manifest_entry.optional:
            return None, "module not available (optional router skipped)"
        return None, "module import failed — needs Brad input"

    sid = safe_id(module_id)
    return f"tools.module_health.check_{sid}", f"tests/module_health/test_{sid}.py"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files or the registry",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(REPO_ROOT))

    entries = load_registry()
    created = 0
    flagged = 0

    if not args.dry_run:
        TEST_DIR.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        if entry.get("health_check") not in ("TODO", "", None) and entry.get("test_suite") not in ("TODO", "", None):
            continue
        if not entry.get("module_path"):
            entry["flag_reason"] = "hub tile / no module_path"
            continue

        health_check, test_suite = classify(entry)

        if health_check is None:
            # Flag this entry instead of writing a placeholder check.
            entry["flag_reason"] = test_suite
            if not args.dry_run:
                entry["last_result"] = {
                    "health_check": test_suite,
                    "test_suite": "flagged",
                }
                entry["status"] = "unverified"
            flagged += 1
            continue

        sid = safe_id(entry["id"])
        test_path = TEST_DIR / f"test_{sid}.py"

        if not args.dry_run:
            test_path.write_text(
                TEST_TEMPLATE.format(module_id=entry["id"], safe_id=sid),
                encoding="utf-8",
            )
            entry["health_check"] = health_check
            entry["test_suite"] = str(test_path.relative_to(REPO_ROOT).as_posix())
            # Clear any previous flag_reason if it was generated.
            entry.pop("flag_reason", None)
        created += 1

    if not args.dry_run:
        # Backup the original registry before overwriting.
        backup = REGISTRY_PATH.with_suffix(".yaml.bak")
        shutil.copy2(REGISTRY_PATH, backup)
        save_registry(entries)

    print(f"Entries examined: {len(entries)}")
    print(f"Test files created: {created}")
    print(f"Entries flagged: {flagged}")
    if not args.dry_run:
        print(f"Registry updated: {REGISTRY_PATH}")
        print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
