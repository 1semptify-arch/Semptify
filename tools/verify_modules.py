"""
verify_modules.py

Reads tools/module_registry.yaml, calls each module's health_check callable,
optionally runs its test suite, and writes back last_verified + status.

Run modes:
  python tools/verify_modules.py            # verify all
  python tools/verify_modules.py --id X     # verify one module
  python tools/verify_modules.py --sync     # run sync_registry.py first, then verify all

This is the backend for the "Update Now" button on the
System Health & Updates tile.
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.core.utc import parse_iso, utc_now  # noqa: E402

REGISTRY_PATH = Path(__file__).resolve().parent / "module_registry.yaml"
STALE_AFTER_DAYS = 7


def load_registry(path: Path = REGISTRY_PATH) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Registry not found at {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def save_registry(entries: list[dict], path: Path = REGISTRY_PATH) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(entries, f, sort_keys=False)


def resolve_health_check(dotted_path: str):
    """
    dotted_path looks like 'modules.invite_codes.health_check'.
    Returns the callable, or None if it can't be resolved.
    """
    if not dotted_path or dotted_path in ("TODO", ""):
        return None
    try:
        module_path, func_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)
    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ! could not resolve health_check '{dotted_path}': {e}")
        return None


def run_test_suite(test_path: str) -> tuple[bool, str]:
    """
    Runs a module's test file via pytest. Returns (passed, summary_message).
    """
    if not test_path or test_path in ("TODO", ""):
        return True, "no test suite configured"
    target = Path(test_path)
    if not target.is_absolute():
        target = Path(__file__).resolve().parent.parent / test_path
    if not target.exists():
        return False, f"test suite not found: {test_path}"
    pytest_cmd = [sys.executable, "-m", "pytest", str(target), "-q"]
    result = subprocess.run(pytest_cmd, capture_output=True, text=True, timeout=120)  # noqa: S603 # nosec B603
    passed = result.returncode == 0
    summary = result.stdout.strip().splitlines()[-1] if result.stdout else result.stderr
    return passed, summary


def _is_stale(last_verified: str | None) -> bool:
    if not last_verified:
        return False
    try:
        dt = parse_iso(last_verified)
    except (ValueError, TypeError):
        return False
    return utc_now() - dt > timedelta(days=STALE_AFTER_DAYS)


def verify_one(entry: dict) -> dict:
    """
    Runs health_check + test_suite for a single registry entry.
    Mutates and returns the entry with updated status/last_verified.
    A module with no checks is unverified (white), not broken.
    """
    module_id = entry.get("id", "UNKNOWN")
    print(f"Verifying {module_id}...")

    health_fn = resolve_health_check(entry.get("health_check", ""))
    health_ok, health_msg = (False, "health_check not configured")
    if health_fn:
        try:
            health_ok, health_msg = health_fn()
            if not isinstance(health_ok, bool):
                health_ok = bool(health_ok)
        except Exception as e:
            health_ok, health_msg = False, f"health_check raised: {e}"

    tests_ok, tests_msg = run_test_suite(entry.get("test_suite", ""))

    # Determine status. Hard-gate: both must pass to be green.
    hc_configured = bool(entry.get("health_check") and entry.get("health_check") != "TODO")
    ts_configured = bool(entry.get("test_suite") and entry.get("test_suite") != "TODO")

    if not hc_configured and not ts_configured:
        entry["status"] = "unverified"
    elif health_ok and tests_ok:
        entry["status"] = "ok"
    elif health_ok or tests_ok:
        entry["status"] = "warning"
    else:
        entry["status"] = "broken"

    # Staleness overrides ok -> warning
    if entry["status"] == "ok" and _is_stale(entry.get("last_verified")):
        entry["status"] = "warning"
        health_msg = f"{health_msg}; stale (> {STALE_AFTER_DAYS} days)"

    entry["last_verified"] = utc_now().isoformat()
    entry["last_result"] = {
        "health_check": health_msg,
        "test_suite": tests_msg,
    }
    print(f"  -> {entry['status']} ({health_msg} / {tests_msg})")
    return entry


def verify_all(target_id: str | None = None) -> list[dict]:
    entries = load_registry()
    for entry in entries:
        if target_id and entry.get("id") != target_id:
            continue
        # Orphaned entries are not auto-re-verified unless explicitly targeted
        if entry.get("status") == "orphaned" and not target_id:
            continue
        verify_one(entry)
    save_registry(entries)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Semptify admin modules")
    parser.add_argument("--id", help="Verify a single module by id")
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Run sync_registry.py first to catch new/orphaned modules",
    )
    args = parser.parse_args()

    if args.sync:
        sync_path = Path(__file__).resolve().parent / "sync_registry.py"
        print("Running registry sync first...")
        result = subprocess.run([sys.executable, str(sync_path), "--write"], check=False)  # noqa: S603 # nosec B603
        if result.returncode != 0:
            print("Registry sync failed; continuing with current registry.", file=sys.stderr)

    verify_all(target_id=args.id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
