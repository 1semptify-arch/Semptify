"""
stub_check.py — wraps the existing tools/stub_detector.py so it runs
as one plugin inside the unified guardrail engine, instead of as a
separate standalone script.

Does NOT reimplement stub detection. Just calls the existing tool and
translates its result into a CheckResult.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from guardrail_engine import CheckResult  # noqa: E402


def run(repo_root: Path) -> CheckResult:
    detector_path = repo_root / "tools" / "stub_detector.py"

    if not detector_path.exists():
        return CheckResult(
            name="stub_check",
            passed=True,
            summary="tools/stub_detector.py not found — skipped (nothing to check).",
        )

    try:
        result = subprocess.run(
            [sys.executable, str(detector_path)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="stub_check",
            passed=False,
            summary="stub_detector.py timed out after 300s — likely an oversized unscanned dir in the tree (e.g. a stray venv copy). Detector prunes known skip dirs during its walk, so a timeout means something new is bloating the scan root.",
        )

    output = (result.stdout or "") + (result.stderr or "")

    # stub_detector.py's own exit code is the source of truth for pass/fail.
    # Non-zero = it found genuine stubs.
    passed = result.returncode == 0

    summary = "No stubs found." if passed else "stub_detector.py reported genuine stubs — see details."

    return CheckResult(
        name="stub_check",
        passed=passed,
        summary=summary,
        details=output if not passed else "",
    )
