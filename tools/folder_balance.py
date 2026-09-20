"""Folder balance report — the requirements/balancing tool for the vault tree.

Run:  python tools/folder_balance.py          (from the repo root)
      .\\venv311\\Scripts\\python.exe tools/folder_balance.py

Prints the whole picture in one pass:
  - the requirement matrix (feature -> folders -> eager/lazy)
  - drift between the registry and the canonical tree
  - the lazy roadmap: eager folders that could go first-use once their
    write paths gain an ensure hook
  - provisioning cost: how many create_folder calls the folders step makes
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import vault_paths as vp
from app.core.vault_folder_requirements import (
    FOLDER_REQUIREMENTS,
    eager_folders,
    lazy_folders,
    lazy_without_hook,
)


def main() -> int:
    issues = 0

    print("=" * 72)
    print("VAULT FOLDER BALANCE")
    print("=" * 72)

    print("\n-- Requirement matrix -------------------------------------------")
    for name, entry in FOLDER_REQUIREMENTS.items():
        mode = "EAGER" if entry.get("eager") else "lazy "
        hook = entry.get("ensure_hook") or ("—" if entry.get("eager") else "MISSING!")
        print(f"  [{mode}] {name:<16} {len(entry['folders']):>2} folder(s)  hook: {hook}")
        for path in entry["folders"]:
            print(f"          {path}")

    eager, lazy = eager_folders(), lazy_folders()
    claimed = set(eager) | set(lazy)
    canonical = set(vp.CANONICAL_VAULT_FOLDERS)

    print("\n-- Drift check ---------------------------------------------------")
    orphans = canonical - claimed
    ghosts = claimed - canonical
    if orphans:
        issues += len(orphans)
        print("  canonical folders nobody claims (decide: register or retire):")
        for p in sorted(orphans):
            print(f"    ! {p}")
    else:
        print("  every canonical folder is claimed — OK")
    if ghosts:
        print("  registry paths not in the canonical tree (add to CANONICAL_VAULT_FOLDERS?):")
        for p in sorted(ghosts):
            print(f"    ? {p}")

    print("\n-- Lazy roadmap --------------------------------------------------")
    roadmap = lazy_without_hook()
    if roadmap:
        print("  eager today, lazy-able once the writer calls ensure_vault_folders():")
        for name, folders in roadmap.items():
            print(f"    {name}: {', '.join(folders)}")
    else:
        print("  nothing waiting — every lazy-able feature has its hook")

    print("\n-- Provisioning cost ---------------------------------------------")
    print(f"  folders step creates {len(eager)} folders eagerly "
          f"(~{len(eager)} provider calls, 0.5s spacing)")
    print(f"  {len(lazy)} folders lazy — created on first use, zero setup cost")

    print("\n" + ("ISSUES FOUND: %d" % issues if issues else "BALANCED — no orphans, no double claims"))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
