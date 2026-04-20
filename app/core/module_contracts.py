"""
Standardized module and function-group contracts.

Purpose:
- Define one plug-and-play contract shape for module capabilities.
- Provide centralized registration + validation for deterministic integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
