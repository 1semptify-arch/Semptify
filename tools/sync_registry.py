"""
sync_registry.py

Reconciles tools/module_registry.yaml against app.core.product_manifest.MANIFEST,
which is the source of truth for "what modules exist" in the running app.

Run modes:
  python tools/sync_registry.py            # sync all manifest modules
  python tools/sync_registry.py --dry-run  # preview changes without writing
  python tools/sync_registry.py --write    # write changes back to registry

Behavior:
  - Manifest module not in registry -> add stub with status: unverified
  - Registry module not in manifest -> mark status: orphaned
  - Module in both -> leave registry data untouched (version/status/last_verified)

The registry lives at tools/module_registry.yaml; Hub tiles with a
pre-defined id are never removed by this tool.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.core.utc import utc_now  # noqa: E402

REGISTRY_PATH = Path(__file__).resolve().parent / "module_registry.yaml"

# Hub tiles are defined manually and should not be auto-removed or overwritten.
HUB_TILE_IDS = {
    "run_modules",
    "testing",
    "invite_codes",
    "correspondence",
    "user_concerns",
    "system_health",
    "advanced",
}


def _load_manifest_modules() -> list[dict]:
    """Import product_manifest and return its registered modules as dicts."""
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from app.core.product_manifest import MANIFEST
    except ImportError as e:
        raise RuntimeError(f"Could not import product manifest: {e}") from e
    finally:
        sys.path.pop(0)

    modules = []
    for entry in MANIFEST.all():
        # Derive a readable module id from the module path + router attribute.
        # app.modules.foo.router with router_attr="router" -> "foo"
        # app.modules.foo.router with router_attr="other_router" -> "foo_other_router"
        # app.core.versioning with router_attr="version_router" -> "versioning"
        parts = entry.module_path.split(".")
        if len(parts) >= 2 and (parts[-1] == entry.router_attr or parts[-1] == "router"):
            name = parts[-2]
        else:
            name = parts[-1] if parts else entry.module_path
        if parts[-1] == "router" and entry.router_attr != "router":
            name = f"{name}_{entry.router_attr}"
        name = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")
        display = " ".join(w.capitalize() for w in name.split("_"))
        if entry.tags:
            display = " / ".join(t.title() for t in entry.tags)

        # Tier A = admin/sensitive; Tier B = advanced/dev/tenant tools
        tier_value = str(entry.tier).lower()
        tier = "A" if tier_value == "admin" or "admin" in entry.requires_role else "B"

        category = "advanced"
        tier_value = str(entry.tier).lower()
        if tier_value == "core":
            category = "core"
        elif tier_value == "admin":
            category = "admin"
        elif tier_value == "dev":
            category = "advanced"
        elif tier_value in ("extended", "advocate"):
            category = "tenant_tool"
        elif tier_value == "research":
            category = "research"

        modules.append(
            {
                "id": name,
                "display_name": display,
                "category": category,
                "tier": tier,
                "owner": "brad",
                "version": "1.0.0",
                "module_path": entry.module_path,
                "health_check": "TODO",
                "test_suite": "TODO",
                "last_verified": None,
                "status": "unverified",
            }
        )
    return modules


def load_registry(path: Path = REGISTRY_PATH) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def save_registry(entries: list[dict], path: Path = REGISTRY_PATH) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(entries, f, sort_keys=False)


def sync_registry(dry_run: bool = False) -> tuple[list[dict], list[str], list[str]]:
    """
    Reconcile manifest against registry. Returns (entries, added_ids, orphaned_ids).
    """
    manifest_modules = _load_manifest_modules()
    entries = load_registry()

    by_id = {e["id"]: e for e in entries}
    added = []
    orphaned = []

    # Add / update from manifest
    for mod in manifest_modules:
        mod_id = mod["id"]
        if mod_id in by_id:
            # Exists in both: leave registry's own data alone, but keep module_path fresh
            existing = by_id[mod_id]
            if not existing.get("module_path") and mod.get("module_path"):
                existing["module_path"] = mod["module_path"]
            continue

        # New manifest module not in registry
        by_id[mod_id] = mod
        entries.append(mod)
        added.append(mod_id)

    # Mark registry entries not in manifest as orphaned, unless they are Hub tiles
    manifest_ids = {m["id"] for m in manifest_modules}
    for entry in entries:
        if entry["id"] in HUB_TILE_IDS:
            continue
        if not entry.get("module_path") or entry["id"] in manifest_ids:
            continue
        if entry.get("status") == "orphaned":
            continue
        entry["status"] = "orphaned"
        entry["last_verified"] = utc_now().isoformat()
        orphaned.append(entry["id"])

    if not dry_run:
        save_registry(entries)

    return entries, added, orphaned


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync module registry against product manifest")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--write", action="store_true", help="Write changes to module_registry.yaml")
    args = parser.parse_args()

    # Default: dry run for safety; user must pass --write to persist
    dry_run = not args.write

    entries, added, orphaned = sync_registry(dry_run=dry_run)

    print(f"Registry: {len(entries)} entries")
    if added:
        print(f"  + added {len(added)} new module(s): {', '.join(added[:10])}{'...' if len(added) > 10 else ''}")
    if orphaned:
        print(f"  ! flagged {len(orphaned)} orphan(s): {', '.join(orphaned[:10])}{'...' if len(orphaned) > 10 else ''}")
    if not added and not orphaned:
        print("  = no changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
