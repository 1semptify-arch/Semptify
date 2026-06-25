"""
Tests for app/core/product_manifest.py

Validates:
- Tier enum completeness
- Manifest has no duplicate entries
- Every entry has non-empty module path and tags
- CORE tier always contains essential modules
- DEV tier is self-contained
- Registration API accepts tiers and rejects empty calls
"""

import pytest

from app.core.product_manifest import (
    ProductTier,
    ModuleEntry,
    MANIFEST,
    register_tiers,
    _load_router,
)


class TestProductTier:
    def test_all_returns_all_tiers(self):
        tiers = ProductTier.all()
        assert len(tiers) == 6
        assert ProductTier.CORE in tiers
        assert ProductTier.EXTENDED in tiers
        assert ProductTier.ADVOCATE in tiers
        assert ProductTier.ADMIN in tiers
        assert ProductTier.RESEARCH in tiers
        assert ProductTier.DEV in tiers

    def test_tier_values_are_lowercase(self):
        for tier in ProductTier.all():
            assert tier.value == tier.value.lower()


class TestModuleEntry:
    def test_default_tag_derived_from_module_name(self):
        entry = ModuleEntry(module_path="app.modules.documents")
        assert "Documents" in entry.tags

    def test_custom_tags_override_default(self):
        entry = ModuleEntry(module_path="app.routers.x", tags=("Custom",))
        assert entry.tags == ("Custom",)

    def test_qualified_name_format(self):
        entry = ModuleEntry(module_path="app.routers.a", router_attr="b")
        assert entry.qualified_name == "app.routers.a:b"

    def test_frozen_prevents_mutation(self):
        entry = ModuleEntry(module_path="app.routers.x")
        with pytest.raises(AttributeError):
            entry.module_path = "changed"


class TestManifestRegistry:
    def test_no_duplicate_entries(self):
        result = MANIFEST.validate()
        assert result["valid"] is True
        assert result["duplicates"] == []

    def test_every_entry_has_module_path(self):
        for entry in MANIFEST.all():
            assert entry.module_path.strip() != ""

    def test_every_entry_has_tags(self):
        for entry in MANIFEST.all():
            assert len(entry.tags) > 0

    def test_core_contains_essential_modules(self):
        core_entries = MANIFEST.by_tier(ProductTier.CORE)
        core_paths = {e.module_path for e in core_entries}

        essentials = {
            "app.modules.health.router",
            "app.modules.storage.router",
            "app.modules.documents.router",
            "app.modules.vault.router",
            "app.modules.mndes.router",
        }
        for essential in essentials:
            assert essential in core_paths, f"{essential} missing from CORE tier"

    def test_extended_modules_are_optional(self):
        extended = MANIFEST.by_tier(ProductTier.EXTENDED)
        for entry in extended:
            assert entry.optional is True, f"{entry.module_path} should be optional"

    def test_dev_modules_are_optional(self):
        dev = MANIFEST.by_tier(ProductTier.DEV)
        for entry in dev:
            assert entry.optional is True, f"{entry.module_path} should be optional"

    def test_mndes_is_required(self):
        mndes = [e for e in MANIFEST.all() if e.module_path == "app.modules.mndes.router"]
        assert len(mndes) == 1
        assert mndes[0].optional is False


class TestLoadRouter:
    def test_load_router_returns_none_for_missing_optional_module(self):
        entry = ModuleEntry(module_path="app.routers.does_not_exist_12345", optional=True)
        result = _load_router(entry)
        assert result is None

    def test_load_router_raises_for_missing_required_module(self):
        entry = ModuleEntry(module_path="app.routers.does_not_exist_12345", optional=False)
        with pytest.raises(RuntimeError):
            _load_router(entry)


class TestRegisterTiers:
    def test_register_tiers_rejects_empty_tiers(self):
        class FakeApp:
            pass

        with pytest.raises(ValueError, match="At least one ProductTier"):
            register_tiers(FakeApp())
