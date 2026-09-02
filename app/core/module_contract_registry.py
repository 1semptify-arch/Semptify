"""In-memory registry for ModuleContract declarations."""
from __future__ import annotations

from app.core.module_contract import ModuleContract


class ModuleContractRegistry:
    """In-memory registry for ModuleContracts keyed by stable ID."""

    def __init__(self) -> None:
        self._contracts: dict[str, ModuleContract] = {}

    def register(self, contract: ModuleContract) -> ModuleContract:
        key = contract.stable_id
        if not key:
            raise ValueError("ModuleContract must have a module_path or contract_id")
        self._contracts[key] = contract
        return contract

    def get(self, contract_id: str) -> ModuleContract | None:
        return self._contracts.get(contract_id)

    def list(self) -> list[ModuleContract]:
        return list(self._contracts.values())

    def clear(self) -> None:
        self._contracts.clear()

    def get_by_module_path(self, module_path: str) -> ModuleContract | None:
        """Look up by dotted module path, whether or not a contract_id is set."""
        if module_path in self._contracts:
            return self._contracts[module_path]
        for contract in self._contracts.values():
            if contract.module_path == module_path:
                return contract
        return None


module_contract_registry = ModuleContractRegistry()


def register_module_contract(contract: ModuleContract) -> ModuleContract:
    """Convenience wrapper for module register.py files."""
    return module_contract_registry.register(contract)
