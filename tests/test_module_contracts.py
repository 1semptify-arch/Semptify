"""Tests for app.core.module_contracts — Function-group contract registry."""

import pytest

from app.core.module_contracts import (
    FunctionGroupContract,
    ModuleContractRegistry,
    contract_registry,
    register_function_group,
)


# ---------------------------------------------------------------------------
# FunctionGroupContract dataclass
# ---------------------------------------------------------------------------
class TestFunctionGroupContract:
    def test_creation(self):
        c = FunctionGroupContract(
            module="vault",
            group_name="upload",
            title="Upload",
            description="Handles uploads",
            inputs=("file",),
            outputs=("result",),
            dependencies=(),
        )
        assert c.module == "vault"
        assert c.deterministic is True

    def test_frozen(self):
        c = FunctionGroupContract(
            module="m",
            group_name="g",
            title="T",
            description="D",
            inputs=(),
            outputs=("o",),
            dependencies=(),
        )
        with pytest.raises(AttributeError):
            c.module = "other"

    def test_to_dict(self):
        c = FunctionGroupContract(
            module="vault",
            group_name="upload",
            title="Upload",
            description="Handles uploads",
            inputs=("file", "meta"),
            outputs=("result",),
            dependencies=("storage",),
            deterministic=False,
        )
        d = c.to_dict()
        assert d["module"] == "vault"
        assert d["group_name"] == "upload"
        assert d["inputs"] == ["file", "meta"]
        assert d["outputs"] == ["result"]
        assert d["dependencies"] == ["storage"]
        assert d["deterministic"] is False


# ---------------------------------------------------------------------------
# ModuleContractRegistry
# ---------------------------------------------------------------------------
class TestModuleContractRegistry:
    def _make_contract(self, module="mod", group="grp", outputs=("out",)):
        return FunctionGroupContract(
            module=module,
            group_name=group,
            title="T",
            description="D",
            inputs=("in",),
            outputs=outputs,
            dependencies=(),
        )

    def test_register_and_get(self):
        reg = ModuleContractRegistry()
        c = self._make_contract()
        reg.register(c)
        assert reg.get("mod", "grp") is c

    def test_get_case_insensitive(self):
        reg = ModuleContractRegistry()
        c = self._make_contract(module="Vault", group="Upload")
        reg.register(c)
        assert reg.get("vault", "upload") is c
        assert reg.get("VAULT", "UPLOAD") is c

    def test_get_strips_whitespace(self):
        reg = ModuleContractRegistry()
        c = self._make_contract(module=" mod ", group=" grp ")
        reg.register(c)
        assert reg.get("mod", "grp") is c

    def test_get_returns_none_for_missing(self):
        reg = ModuleContractRegistry()
        assert reg.get("x", "y") is None

    def test_list_contracts(self):
        reg = ModuleContractRegistry()
        c1 = self._make_contract(module="a", group="g1")
        c2 = self._make_contract(module="b", group="g2")
        reg.register(c1)
        reg.register(c2)
        listed = reg.list_contracts()
        assert len(listed) == 2
        assert c1 in listed
        assert c2 in listed

    def test_overwrite_same_key(self):
        reg = ModuleContractRegistry()
        c1 = self._make_contract(module="m", group="g")
        c2 = self._make_contract(module="m", group="g")
        reg.register(c1)
        reg.register(c2)
        assert reg.list_contracts() == [c2]

    def test_validate_pass(self):
        reg = ModuleContractRegistry()
        reg.register(self._make_contract())
        result = reg.validate()
        assert result["status"] == "pass"
        assert result["summary"]["total_contracts"] == 1
        assert result["summary"]["violations"] == 0

    def test_validate_empty_module(self):
        reg = ModuleContractRegistry()
        c = FunctionGroupContract(
            module="  ",
            group_name="g",
            title="T",
            description="D",
            inputs=(),
            outputs=("o",),
            dependencies=(),
        )
        reg.register(c)
        result = reg.validate()
        assert result["status"] == "fail"
        assert any("module must be non-empty" in v["reason"] for v in result["violations"])

    def test_validate_empty_group_name(self):
        reg = ModuleContractRegistry()
        c = FunctionGroupContract(
            module="m",
            group_name="  ",
            title="T",
            description="D",
            inputs=(),
            outputs=("o",),
            dependencies=(),
        )
        reg.register(c)
        result = reg.validate()
        assert result["status"] == "fail"
        assert any("group_name must be non-empty" in v["reason"] for v in result["violations"])

    def test_validate_no_outputs(self):
        reg = ModuleContractRegistry()
        c = FunctionGroupContract(
            module="m",
            group_name="g",
            title="T",
            description="D",
            inputs=(),
            outputs=(),
            dependencies=(),
        )
        reg.register(c)
        result = reg.validate()
        assert result["status"] == "fail"
        assert any("outputs must define at least one key" in v["reason"] for v in result["violations"])


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------
class TestModuleLevelHelpers:
    def test_register_function_group(self):
        c = FunctionGroupContract(
            module="test_helper_mod",
            group_name="test_helper_grp",
            title="T",
            description="D",
            inputs=(),
            outputs=("o",),
            dependencies=(),
        )
        returned = register_function_group(c)
        assert returned is c
        assert contract_registry.get("test_helper_mod", "test_helper_grp") is c
