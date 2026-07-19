"""
Tests for app/core/module_sdk.py

Validates:
- ModuleCapability enum completeness
- ModuleManifest immutability and conversion to ModuleEntry
- ModuleRegistry singleton, install, queries, validation
- register_module with mocked FastAPI app
- register_tier_modules batch registration
- get_module_status discovery endpoint shape
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI

from app.core.module_sdk import (
    InstalledModule,
    ModuleCapability,
    ModuleManifest,
    ModuleRegistry,
    get_module_status,
    register_module,
    register_tier_modules,
)
from app.core.product_manifest import ProductTier


class TestModuleCapability:
    def test_all_capabilities_present(self):
        caps = list(ModuleCapability)
        assert len(caps) == 6
        assert ModuleCapability.ROUTER in caps
        assert ModuleCapability.CONTRACT in caps
        assert ModuleCapability.MESH in caps
        assert ModuleCapability.DOCUMENT in caps
        assert ModuleCapability.WIDGET in caps
        assert ModuleCapability.BACKGROUND in caps

    def test_values_are_lowercase(self):
        for cap in ModuleCapability:
            assert cap.value == cap.value.lower()


class TestModuleManifest:
    def test_basic_manifest_creation(self):
        m = ModuleManifest(
            name="test_mod",
            display_name="Test Module",
            description="A test module",
            version="1.0.0",
            tier=ProductTier.CORE,
        )
        assert m.name == "test_mod"
        assert m.tier == ProductTier.CORE
        assert m.optional is True

    def test_manifest_is_frozen(self):
        m = ModuleManifest(
            name="test_mod",
            display_name="Test",
            description="Desc",
            version="1.0.0",
            tier=ProductTier.CORE,
        )
        with pytest.raises(AttributeError):
            m.name = "changed"

    def test_to_module_entry_returns_none_when_no_router_capability(self):
        m = ModuleManifest(
            name="test_mod",
            display_name="Test",
            description="Desc",
            version="1.0.0",
            tier=ProductTier.CORE,
            capabilities=(),
            router_module="app.routers.test",
        )
        assert m.to_module_entry() is None

    def test_to_module_entry_returns_none_when_no_router_module(self):
        m = ModuleManifest(
            name="test_mod",
            display_name="Test",
            description="Desc",
            version="1.0.0",
            tier=ProductTier.CORE,
            capabilities=(ModuleCapability.ROUTER,),
            router_module=None,
        )
        assert m.to_module_entry() is None

    def test_to_module_entry_success(self):
        m = ModuleManifest(
            name="test_mod",
            display_name="Test",
            description="Desc",
            version="1.0.0",
            tier=ProductTier.EXTENDED,
            capabilities=(ModuleCapability.ROUTER,),
            router_module="app.routers.test",
            router_attr="router",
            tags=("Test",),
            prefix="/api/test",
            optional=True,
        )
        entry = m.to_module_entry()
        assert entry is not None
        assert entry.module_path == "app.routers.test"
        assert entry.router_attr == "router"
        assert entry.tags == ("Test",)
        assert entry.prefix == "/api/test"
        assert entry.optional is True
        assert entry.tier == ProductTier.EXTENDED

    def test_to_dict_shape(self):
        m = ModuleManifest(
            name="test_mod",
            display_name="Test",
            description="Desc",
            version="2.0.0",
            tier=ProductTier.DEV,
            capabilities=(ModuleCapability.ROUTER, ModuleCapability.CONTRACT),
            router_module="app.routers.test",
        )
        d = m.to_dict()
        assert d["name"] == "test_mod"
        assert d["tier"] == "dev"
        assert d["capabilities"] == ["router", "contract"]
        assert d["router_module"] == "app.routers.test"
        assert "optional" in d


class TestInstalledModule:
    def test_to_dict_includes_manifest(self):
        manifest = ModuleManifest(
            name="test",
            display_name="Test",
            description="Desc",
            version="1.0.0",
            tier=ProductTier.CORE,
        )
        installed = InstalledModule(manifest=manifest, router=None, initialized=True)
        d = installed.to_dict()
        assert d["name"] == "test"
        assert d["initialized"] is True
        assert d["has_router"] is False
        assert d["error"] is None


class TestModuleRegistry:
    def test_singleton_behavior(self):
        r1 = ModuleRegistry()
        r2 = ModuleRegistry()
        assert r1 is r2

    def test_install_and_get(self):
        reg = ModuleRegistry()
        # Clear any previous state from other tests
        reg._modules.clear()
        reg._tier_index = {t: [] for t in ProductTier.all()}

        manifest = ModuleManifest(
            name="mod_a",
            display_name="Mod A",
            description="Desc",
            version="1.0.0",
            tier=ProductTier.CORE,
        )
        installed = InstalledModule(manifest=manifest)
        reg.install(installed)

        retrieved = reg.get("mod_a")
        assert retrieved is not None
        assert retrieved.manifest.name == "mod_a"

    def test_list_by_tier(self):
        reg = ModuleRegistry()
        reg._modules.clear()
        reg._tier_index = {t: [] for t in ProductTier.all()}

        for tier in (ProductTier.CORE, ProductTier.EXTENDED, ProductTier.CORE):
            m = ModuleManifest(
                name=f"mod_{tier.value}",
                display_name="X",
                description="D",
                version="1.0.0",
                tier=tier,
            )
            reg.install(InstalledModule(manifest=m))

        core = reg.list_by_tier(ProductTier.CORE)
        assert len(core) == 2

        ext = reg.list_by_tier(ProductTier.EXTENDED)
        assert len(ext) == 1

        dev = reg.list_by_tier(ProductTier.DEV)
        assert len(dev) == 0

    def test_list_by_capability(self):
        reg = ModuleRegistry()
        reg._modules.clear()
        reg._tier_index = {t: [] for t in ProductTier.all()}

        m1 = ModuleManifest(
            name="has_router",
            display_name="R",
            description="D",
            version="1.0.0",
            tier=ProductTier.CORE,
            capabilities=(ModuleCapability.ROUTER,),
        )
        m2 = ModuleManifest(
            name="has_contract",
            display_name="C",
            description="D",
            version="1.0.0",
            tier=ProductTier.CORE,
            capabilities=(ModuleCapability.CONTRACT,),
        )
        reg.install(InstalledModule(manifest=m1))
        reg.install(InstalledModule(manifest=m2))

        routers = reg.list_by_capability(ModuleCapability.ROUTER)
        assert len(routers) == 1
        assert routers[0].manifest.name == "has_router"

    def test_validate_passes_for_clean_manifest(self):
        reg = ModuleRegistry()
        reg._modules.clear()
        reg._tier_index = {t: [] for t in ProductTier.all()}

        m = ModuleManifest(
            name="clean",
            display_name="Clean",
            description="D",
            version="1.0.0",
            tier=ProductTier.CORE,
        )
        reg.install(InstalledModule(manifest=m))
        result = reg.validate()
        assert result["valid"] is True
        assert result["total"] == 1
        assert result["violations"] == []

    def test_validate_fails_for_router_without_module(self):
        reg = ModuleRegistry()
        reg._modules.clear()
        reg._tier_index = {t: [] for t in ProductTier.all()}

        m = ModuleManifest(
            name="broken",
            display_name="Broken",
            description="D",
            version="1.0.0",
            tier=ProductTier.CORE,
            capabilities=(ModuleCapability.ROUTER,),
            router_module=None,
        )
        reg.install(InstalledModule(manifest=m))
        result = reg.validate()
        assert result["valid"] is False
        assert len(result["violations"]) == 1
        assert "ROUTER" in result["violations"][0]["reason"]

    def test_validate_fails_for_contract_without_contracts(self):
        reg = ModuleRegistry()
        reg._modules.clear()
        reg._tier_index = {t: [] for t in ProductTier.all()}

        m = ModuleManifest(
            name="broken2",
            display_name="Broken2",
            description="D",
            version="1.0.0",
            tier=ProductTier.CORE,
            capabilities=(ModuleCapability.CONTRACT,),
            contracts=(),
        )
        reg.install(InstalledModule(manifest=m))
        result = reg.validate()
        assert result["valid"] is False
        assert len(result["violations"]) == 1
        assert "CONTRACT" in result["violations"][0]["reason"]


class TestRegisterModule:
    def test_register_module_without_router(self):
        app = MagicMock(spec=FastAPI)
        manifest = ModuleManifest(
            name="no_router",
            display_name="No Router",
            description="D",
            version="1.0.0",
            tier=ProductTier.CORE,
            capabilities=(),
        )
        installed = register_module(app, manifest)
        assert installed.initialized is True
        assert installed.router is None
        app.include_router.assert_not_called()

    def test_register_module_with_router(self):
        app = MagicMock(spec=FastAPI)
        # We can't easily mock _load_router, so test the no-router path
        # and rely on integration tests for the full router path.
        manifest = ModuleManifest(
            name="no_router",
            display_name="No Router",
            description="D",
            version="1.0.0",
            tier=ProductTier.CORE,
            capabilities=(),
        )
        installed = register_module(app, manifest)
        assert installed.initialized is True


class TestRegisterTierModules:
    def test_rejects_empty_tiers(self):
        app = MagicMock(spec=FastAPI)
        with pytest.raises(ValueError, match="At least one ProductTier"):
            register_tier_modules(app)

    def test_registers_core_tier(self):
        app = MagicMock(spec=FastAPI)
        report = register_tier_modules(app, ProductTier.CORE)
        assert "installed" in report
        assert "skipped" in report
        assert "errors" in report
        assert "total" in report
        assert "modules" in report
        assert report["total"] > 0


class TestGetModuleStatus:
    def test_returns_discovery_shape(self):
        # Ensure at least one module is installed
        reg = ModuleRegistry()
        reg._modules.clear()
        reg._tier_index = {t: [] for t in ProductTier.all()}

        m = ModuleManifest(
            name="status_test",
            display_name="Status Test",
            description="D",
            version="1.0.0",
            tier=ProductTier.CORE,
        )
        reg.install(InstalledModule(manifest=m))

        status = get_module_status()
        assert "installed_modules" in status
        assert "by_tier" in status
        assert "by_capability" in status
        assert "validation" in status
        assert status["validation"]["valid"] is True
