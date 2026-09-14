"""
Standardized module and function-group contracts.

Purpose:
- Define one plug-and-play contract shape for module capabilities.
- Provide centralized registration + validation for deterministic integration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContractStage:
    """One stage of a staged function flow (gated stage navigation).

    Declared on FunctionGroupContract.stages. The UI layer renders the
    function-nav rail from these: the stage label + progress pips, a Back
    action, quiet secondary actions, and the stage's forward action which
    stays visibly locked until every field named in `requires` is satisfied.

    This is in-task ordering, not access gating — it hides/defers actions
    that cannot run yet, it never removes access to a function.
    """

    id: str  # stable stage id, e.g. "choose_file"
    label: str  # shown in the rail, e.g. "Choose the file"
    action: str  # forward-action label, e.g. "Save journal entry"
    requires: tuple[str, ...] = ()  # form field names that must be non-empty to unlock `action`
    skippable: bool = False  # whether a Skip action appears at this stage


@dataclass(frozen=True)
class FunctionGroupContract:
    """Standard contract for a function-group within a module."""

    module: str
    group_name: str
    title: str
    description: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    dependencies: tuple[str, ...]
    deterministic: bool = True

    # Data-sensitivity and route conformance metadata (added 2026-07-29 for
    # Build Orchestrator hard-gate contract validation).
    tier: str = ""  # T0 / T1 / T2 / T3 — see AGENTS.md
    allowed_routes: tuple[str, ...] = ()  # canonical route paths, e.g. "/api/disputes"
    allowed_prefixes: tuple[str, ...] = ()  # URL prefixes this group may register

    # Staged function navigation (added 2026-09-14). Empty = single-stage
    # page, no rail rendered. When set, the guide-page shell renders the
    # .fnav rail: progress pips + only the actions valid at the current
    # stage (back / quiet actions / the gated forward action).
    stages: tuple[ContractStage, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "group_name": self.group_name,
            "title": self.title,
            "description": self.description,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "dependencies": list(self.dependencies),
            "deterministic": self.deterministic,
            "tier": self.tier,
            "allowed_routes": list(self.allowed_routes),
            "allowed_prefixes": list(self.allowed_prefixes),
            "stages": [
                {
                    "id": s.id,
                    "label": s.label,
                    "action": s.action,
                    "requires": list(s.requires),
                    "skippable": s.skippable,
                }
                for s in self.stages
            ],
        }


class ModuleContractRegistry:
    """In-memory registry for function-group contracts."""

    def __init__(self) -> None:
        self._contracts: dict[str, FunctionGroupContract] = {}

    @staticmethod
    def _make_key(module: str, group_name: str) -> str:
        return f"{module.strip().lower()}::{group_name.strip().lower()}"

    def register(self, contract: FunctionGroupContract) -> FunctionGroupContract:
        key = self._make_key(contract.module, contract.group_name)
        self._contracts[key] = contract
        return contract

    def list_contracts(self) -> list[FunctionGroupContract]:
        return list(self._contracts.values())

    def get(self, module: str, group_name: str) -> FunctionGroupContract | None:
        return self._contracts.get(self._make_key(module, group_name))

    def validate(self) -> dict[str, Any]:
        violations: list[dict[str, str]] = []

        for contract in self._contracts.values():
            if not contract.module.strip():
                violations.append(
                    {
                        "contract": f"{contract.module}::{contract.group_name}",
                        "reason": "module must be non-empty",
                    }
                )
            if not contract.group_name.strip():
                violations.append(
                    {
                        "contract": f"{contract.module}::{contract.group_name}",
                        "reason": "group_name must be non-empty",
                    }
                )
            if len(contract.outputs) == 0:
                violations.append(
                    {
                        "contract": f"{contract.module}::{contract.group_name}",
                        "reason": "outputs must define at least one key",
                    }
                )

        return {
            "status": "pass" if not violations else "fail",
            "summary": {
                "total_contracts": len(self._contracts),
                "violations": len(violations),
            },
            "violations": violations,
        }


contract_registry = ModuleContractRegistry()


def register_function_group(contract: FunctionGroupContract) -> FunctionGroupContract:
    return contract_registry.register(contract)
