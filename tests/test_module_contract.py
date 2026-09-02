"""Tests for the ModuleContract layer and its integration with PageContract."""
from __future__ import annotations

import pytest

from app.core.module_contract import ModuleContract, ModuleContractErrorRoute
from app.core.module_contract_registry import module_contract_registry

# Importing the register modules populates the registry with sample contracts.
import app.modules.page_composer.register  # noqa: F401
import app.modules.page_shell.register  # noqa: F401


class TestModuleContractRegistry:
    def test_registry_has_sample_contracts(self) -> None:
        contracts = module_contract_registry.list()
        paths = {c.module_path for c in contracts}
        assert "app.modules.page_shell" in paths
        assert "app.modules.page_composer" in paths

    def test_get_by_module_path(self) -> None:
        contract = module_contract_registry.get_by_module_path("app.modules.page_shell")
        assert contract is not None
        assert contract.title.startswith("Page Shell")
        assert contract.pillar == "record"

    def test_module_contract_stable_id(self) -> None:
        contract = ModuleContract(
            module_path="app.modules.test",
            title="Test",
            pillar="know",
            contract_id="custom::id",
        )
        assert contract.stable_id == "custom::id"

    def test_module_contract_without_contract_id_uses_path(self) -> None:
        contract = ModuleContract(
            module_path="app.modules.no_id",
            title="No ID",
            pillar="act",
        )
        assert contract.stable_id == "app.modules.no_id"

    def test_error_route_defaults_to_help(self) -> None:
        contract = ModuleContract(module_path="app.modules.x", title="X", pillar="govern")
        assert contract.error_route.route_to == "help"


class TestModuleContractToPageContract:
    def test_page_contract_can_reference_module_contract(self) -> None:
        from app.modules.page_shell.page_contract import PageContract

        contract = PageContract(
            page_id="demo_page",
            page_title="Demo",
            pillar="record",
            module_contract_id="app.modules.page_shell",
            narrative_ref="ctx_explain/demo",
        )
        assert contract.module_contract_id == "app.modules.page_shell"
        assert contract.narrative_ref == "ctx_explain/demo"

    def test_narrative_ref_survives_to_page_config(self) -> None:
        from app.modules.page_shell.page_contract import PageContract

        contract = PageContract(
            page_id="demo_page_2",
            page_title="Demo 2",
            pillar="know",
            narrative_ref="ctx_explain/demo_2",
        )
        config = contract.to_page_config()
        know_zone = config.zones["know"]
        narrative_blocks = [b for b in know_zone.blocks if b.block_id == "narrative"]
        assert len(narrative_blocks) == 1
        assert narrative_blocks[0].content_ref == "ctx_explain/demo_2"


class TestModuleContractBackfill:
    def test_backfill_derives_from_function_group_contracts(self) -> None:
        from app.core.contract_loader import load_all_contracts
        from app.core.module_contract_registry import module_contract_registry

        # Clear any test-time samples, then load all contract modules and derive.
        module_contract_registry.clear()
        load_all_contracts()

        contracts = module_contract_registry.list()
        assert len(contracts) >= 10, f"Expected at least 10 module contracts, got {len(contracts)}"

        # Spot-check a few modules that are known to have FunctionGroupContracts.
        vault = module_contract_registry.get_by_module_path("app.modules.vault")
        assert vault is not None
        assert "vault::" in vault.function_group_ids[0]

        storage = module_contract_registry.get_by_module_path("app.modules.storage")
        assert storage is not None
        assert storage.dependencies

    def test_backfill_respects_manifest_lifecycle(self) -> None:
        from app.core.contract_loader import load_all_contracts
        from app.core.module_contract_registry import module_contract_registry

        module_contract_registry.clear()
        load_all_contracts()

        page_shell = module_contract_registry.get_by_module_path("app.modules.page_shell")
        assert page_shell is not None
        # Lifecycle should be filled from the manifest (real value depends on manifest).
        assert page_shell.lifecycle in {
            "stable",
            "beta",
            "experimental",
            "dev_only",
            "preview",
            "internal",
            "deprecated",
        }
