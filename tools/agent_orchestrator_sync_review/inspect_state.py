"""Print the current state of the orchestrator sync files.

Run from the repo root:
    python tools/agent_orchestrator_sync_review/inspect_state.py
"""

import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent
    stub_path = repo_root / "tools" / "stub_tasks_new.json"
    tasks_path = repo_root / "tools" / "agent_orchestrator_tasks.json"
    workbook_path = repo_root / "Semptify_Master_Inventory_LIVE_reviewed.xlsx"
    root_stub_path = repo_root / "stub_tasks.json"

    print("=== File existence ===")
    for p in [workbook_path, tasks_path, stub_path, root_stub_path]:
        print(f"{p.relative_to(repo_root)}: exists={p.exists()}, size={p.stat().st_size if p.exists() else 0} bytes")

    if stub_path.exists():
        stubs = json.loads(stub_path.read_text(encoding="utf-8"))
        print(f"\n=== stub_tasks_new.json ===\nTotal stubs: {len(stubs)}")
    else:
        stubs = []
        print("\n=== stub_tasks_new.json ===\nNot found")

    if tasks_path.exists():
        tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
        print(f"\n=== agent_orchestrator_tasks.json ===\nTotal tasks: {len(tasks)}")
        status_counts = {}
        for t in tasks:
            status_counts[t.get("status", "?")] = status_counts.get(t.get("status", "?"), 0) + 1
        print("Status counts:", status_counts)

        by_path = {}
        for t in tasks:
            fp = t.get("file_path", "")
            if fp:
                by_path.setdefault(fp, []).append(t.get("status", "?"))

        missing = [fp for fp in sorted(by_path) if not (repo_root / fp).exists()]
        print(f"Missing paths (out of {len(by_path)} unique): {len(missing)}")
        for fp in missing:
            print(f"  MISSING: {fp}")
    else:
        tasks = []
        print("\n=== agent_orchestrator_tasks.json ===\nNot found")

    print("\n=== Git config ===")
    import subprocess

    result = subprocess.run(
        ["git", "config", "core.hooksPath"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    print("core.hooksPath:", result.stdout.strip() or "(not set)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
