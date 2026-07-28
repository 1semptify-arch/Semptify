"""Tests for the fees_policy guardrail plugin.

The guardrail ensures that no module marked fees_policy=exempt_advanced is
reachable by the tenant role. That distinction protects tenant-facing modules
from implying Semptify charges fees while allowing advanced/admin/research
modules to use "fee" as a landlord-conduct domain term.
"""

import importlib.util
import sys
from pathlib import Path

from app.core.product_manifest import CAPABILITY_DEFAULTS, MANIFEST, FeesPolicy

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _load_fees_policy_check():
    """Load the guardrail plugin the same way guardrail_engine does."""
    spec = importlib.util.spec_from_file_location(
        "fees_policy_check",
        str(TOOLS_DIR / "checks" / "fees_policy_check.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fees_module = _load_fees_policy_check()


class TestFeesPolicyGuardrail:
    def test_real_manifest_passes(self):
        """The current manifest must have no exempt_advanced module reachable by tenants."""
        result = fees_module.run(REPO_ROOT)
        assert result.passed, result.details
        assert "No exempt_advanced module is reachable" in result.summary

    def test_exempt_and_tenant_reachable_fails(self):
        """A fake exempt module in tenant defaults must fail the guardrail."""
        fake_entry = fees_module._FakeEntry(
            module_path="app.modules.fake_advanced.router",
            fees_policy_value=FeesPolicy.EXEMPT_ADVANCED.value,
            requires_role=(),
        )
        result = fees_module.check_manifest(
            [fake_entry],
            {"tenant": ["app.modules.fake_advanced.router"]},
        )
        assert not result.passed
        assert "app.modules.fake_advanced.router" in result.details

    def test_tenant_no_fees_module_is_allowed_for_tenants(self):
        """A tenant_no_fees module in tenant defaults is allowed."""
        fake_entry = fees_module._FakeEntry(
            module_path="app.modules.fake_public.router",
            fees_policy_value=FeesPolicy.TENANT_NO_FEES.value,
            requires_role=(),
        )
        result = fees_module.check_manifest(
            [fake_entry],
            {"tenant": ["app.modules.fake_public.router"]},
        )
        assert result.passed

    def test_exempt_with_requires_role_tenant_fails(self):
        """An exempt module whose requires_role includes tenant must fail."""
        fake_entry = fees_module._FakeEntry(
            module_path="app.modules.fake_research.router",
            fees_policy_value=FeesPolicy.EXEMPT_ADVANCED.value,
            requires_role=("tenant", "admin"),
        )
        result = fees_module.check_manifest(
            [fake_entry],
            {"tenant": []},
        )
        assert not result.passed
        assert "tenant role can reach it" in result.details

    def test_capability_defaults_preserved_in_check(self):
        """The real tenant default list should not contain any exempt module."""
        tenant_modules = set(CAPABILITY_DEFAULTS.get("tenant", []))
        exempt = [e for e in MANIFEST.all() if e.fees_policy == FeesPolicy.EXEMPT_ADVANCED]
        overlap = {e.module_path for e in exempt if e.module_path in tenant_modules}
        assert not overlap, f"exempt_advanced modules in tenant defaults: {overlap}"
