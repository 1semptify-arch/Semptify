"""
manifest_sync_check.py — wraps the existing tools/sync_orchestrator.py
(already wired into your pre-commit hook today) so it becomes one
plugin inside the unified engine instead of its own separate hook entry.

Does NOT reimplement the manifest/sync logic. Just calls the existing
tool and translates its result into a CheckResult.

NOTE: this is also the tool that reported the "16 vs 171 tasks" mismatch
mentioned in BUILD_STATE.md. That mismatch will show up here as a FAIL
(or a suspicious low count in the summary) until it's resolved — that's
intentional, not a bug in this wrapper.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from guardrail_engine import CheckResult  # noqa: E402


def run(repo_root: Path) -> CheckResult:
    orchestrator_path = repo_root / "tools" / "sync_orchestrator.py"

    if not orchestrator_path.exists():
        return CheckResult(
            name="manifest_sync_check",
            passed=True,
            summary="tools/sync_orchestrator.py not found — skipped (nothing to check).",
        )

    result = subprocess.run(
        [sys.executable, str(orchestrator_path), "--check"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = (result.stdout or "") + (result.stderr or "")
    passed = result.returncode == 0

    summary = "Sync orchestrator passed." if passed else "Sync orchestrator reported issues — see details."

    return CheckResult(
        name="manifest_sync_check",
        passed=passed,
        summary=summary,
        details=output if not passed else "",
    )
