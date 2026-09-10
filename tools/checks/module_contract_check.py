"""module_contract_check.py — validate module_contract.json files and the registry index.

Part 1 of SEMPTIFY_BUILD_CONTRACT.md requires every new module to ship a
module_contract.json. This check:
  1. Discovers app/modules/<name>/module_contract.json files.
  2. Validates each against app.core.module_contract.ModuleContract.
  3. Re-computes docs/registry/module_contracts_index.json and fails if it
     does not match the generated output (i.e. the index is stale).

The check is forward-only: modules without a module_contract.json are logged
as missing but do not fail the build, matching the contract's retroactivity rule.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Guardrail plugins live in tools/checks/; the repo root is two levels up.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from guardrail_engine import CheckResult  # noqa: E402


def _index_up_to_date(expected: list[dict], index_path: Path) -> tuple[bool, str]:
    if not index_path.exists():
        return False, f"registry index missing at {index_path}"
    try:
        existing = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"registry index is not valid JSON: {exc}"

    if existing != {"version": "1", "entries": expected}:
        return False, "registry index is stale or differs from generated output"

    return True, "registry index matches generated output"


def run(repo_root: Path) -> CheckResult:
    """Validate module_contract.json files and the generated registry index."""
    from app.core.module_contract import (
        ModuleContractRegistry,
        validate_all_module_contracts,
    )

    validation = validate_all_module_contracts()
    if validation["status"] != "pass":
        details = "\n".join(
            f"{v['module']}: {v['reason']}"
            for v in validation["violations"]
        )
        return CheckResult(
            name="module_contract_check",
            passed=False,
            summary=f"{len(validation['violations'])} module_contract.json validation failure(s).",
            details=details,
        )

    registry = ModuleContractRegistry()
    registry.load()

    index_path = repo_root / "docs" / "registry" / "module_contracts_index.json"
    expected = registry.generate_index(output_path=index_path)

    up_to_date, message = _index_up_to_date(expected, index_path)
    if not up_to_date:
        return CheckResult(
            name="module_contract_check",
            passed=False,
            summary="Module contract registry index is stale or missing.",
            details=message,
        )

    summary = (
        f"{len(expected)} module_contract.json file(s) validated; "
        "registry index is up to date."
    )
    return CheckResult(
        name="module_contract_check",
        passed=True,
        summary=summary,
    )
