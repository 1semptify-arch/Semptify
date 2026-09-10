"""resource_intake_check.py — hard gate for the Information Composer resource pool.

Part 3 of SEMPTIFY_BUILD_CONTRACT.md requires every item in the compiled
Composer resource pool to:
  - have ai_generated: false
  - have a non-empty approved_by value
  - be approved (approval_status == "Approved")
  - be fact-checked (fact_check_status == "Verified")

This guardrail fails the build if any item in data/composer_resources.json
violates those rules.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from guardrail_engine import CheckResult  # noqa: E402


def run(repo_root: Path) -> CheckResult:
    """Validate the compiled Information Composer resource pool."""
    from app.modules.resource_intake.engine import ResourceIntakeEngine

    pool_path = repo_root / "data" / "composer_resources.json"
    if not pool_path.exists():
        return CheckResult(
            name="resource_intake_check",
            passed=False,
            summary="Information Composer resource pool is missing.",
            details="Expected data/composer_resources.json to exist.",
        )

    engine = ResourceIntakeEngine(pool_path=pool_path)
    result = engine.validate_pool()

    if result["status"] != "pass":
        return CheckResult(
            name="resource_intake_check",
            passed=False,
            summary=f"{len(result['violations'])} resource pool violation(s).",
            details="\n".join(result["violations"]),
        )

    return CheckResult(
        name="resource_intake_check",
        passed=True,
        summary=f"{result['count']} resource(s) verified; all are human-approved and non-AI-generated.",
    )
