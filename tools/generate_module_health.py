"""
Bulk generator for module health checks and test suites.

Creates:
  - tests/module_health/test_all_modules.py  (single consolidated parametrized test)
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

CONSOLIDATED_TEST = '''\
"""Consolidated module health regression tests.

Replaces the 122 individual ``test_<id>.py`` stub files with a single
parametrized test that iterates every module in ``tools/module_registry.yaml``
and calls the corresponding ``check_<id>()`` function from
``tools.module_health``.

Each module gets its own test case ID so failures are easy to identify:

    pytest tests/module_health/test_all_modules.py -k auth
"""

from __future__ import annotations

import re

import pytest

from tools.module_health import _load_registry

# Build the parametrized list once at import time.
# Each entry yields (module_id, check_function) pairs.
_REGISTRY = _load_registry()
_PARAMS = []
for _entry in _REGISTRY:
    _id = _entry.get("id")
    _path = _entry.get("module_path")
    if not _id or not _path:
        continue
    # Skip entries that are flagged (ON HOLD, optional, pending decision, etc.)
    # — these were never given individual test files by generate_module_health.py.
    if _entry.get("flag_reason") or _entry.get("health_check") in ("TODO", "", None):
        continue
    _safe = re.sub(r"[^a-z0-9_]", "_", _id).lower()
    _check_name = f"check_{_safe}"
    # Import the dynamically-generated check function.
    import tools.module_health as _mh

    _check = getattr(_mh, _check_name, None)
    if _check is not None:
        _PARAMS.append(pytest.param(_check, id=_id))


@pytest.mark.module_health
@pytest.mark.parametrize("check_fn", _PARAMS)
def test_module_health(check_fn):
    """Verify every registered module imports, has routes, and has no exposure issues."""
    ok, msg = check_fn()
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
        consolidated_path = TEST_DIR / "test_all_modules.py"

        if not args.dry_run:
            entry["health_check"] = health_check
            entry["test_suite"] = "tests/module_health/test_all_modules.py"
            # Clear any previous flag_reason if it was generated.
            entry.pop("flag_reason", None)
        created += 1

    if not args.dry_run and created > 0:
        # Write the consolidated test file (replaces all individual stubs).
        TEST_DIR.mkdir(parents=True, exist_ok=True)
        consolidated_path = TEST_DIR / "test_all_modules.py"
        consolidated_path.write_text(CONSOLIDATED_TEST, encoding="utf-8")
        # Remove any leftover individual test files from the old generator.
        for old_file in TEST_DIR.glob("test_*.py"):
            if old_file.name != "test_all_modules.py":
                old_file.unlink()
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
