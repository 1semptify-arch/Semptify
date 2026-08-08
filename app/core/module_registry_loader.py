"""
Module Registry Loader
======================

FastAPI-safe loader for tools/module_registry.yaml. Used by the
/admin/api endpoints to expose registry state and trigger
verification without re-implementing the YAML logic in main.py.
"""

from __future__ import annotations

import asyncio
import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

from app.core.utc import parse_iso, utc_now

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = REPO_ROOT / "tools" / "module_registry.yaml"
SYNC_SCRIPT = REPO_ROOT / "tools" / "sync_registry.py"
VERIFY_SCRIPT = REPO_ROOT / "tools" / "verify_modules.py"


def load_registry() -> list[dict[str, Any]]:
    """Load the module registry as a list of dicts."""
    if not REGISTRY_PATH.exists():
        return []
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def save_registry(entries: list[dict[str, Any]]) -> None:
    with REGISTRY_PATH.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(entries, f, sort_keys=False)


def get_tile_entries() -> list[dict[str, Any]]:
    """Return registry entries whose IDs match known Hub tiles."""
    hub_ids = {
        "run_modules",
        "testing",
        "invite_codes",
        "correspondence",
        "user_concerns",
        "system_health",
        "advanced",
    }
    return [e for e in load_registry() if e.get("id") in hub_ids]


def is_stale(last_verified: str | None, days: int = 7) -> bool:
    if not last_verified:
        return False
    try:
        dt = parse_iso(last_verified)
    except (ValueError, TypeError):
        return False
    return utc_now() - dt > timedelta(days=days)


def _run_sync_and_verify_sync(target_id: str | None = None) -> list[dict[str, Any]]:
    """
    Run sync_registry.py --write, then verify_modules.py.
    Returns the updated registry.
    """
    result = subprocess.run([str(SYNC_SCRIPT), "--write"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)  # noqa: S603 # nosec B603
    if result.returncode != 0:
        raise RuntimeError(f"sync_registry failed: {result.stderr}")

    cmd = [str(VERIFY_SCRIPT)]
    if target_id:
        cmd.extend(["--id", target_id])
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)  # noqa: S603 # nosec B603
    if result.returncode != 0:
        raise RuntimeError(f"verify_modules failed: {result.stderr}")

    return load_registry()


async def run_sync_and_verify(target_id: str | None = None) -> list[dict[str, Any]]:
    """Async wrapper that offloads the sync + verify subprocess work to a thread."""
    return await asyncio.to_thread(_run_sync_and_verify_sync, target_id)
