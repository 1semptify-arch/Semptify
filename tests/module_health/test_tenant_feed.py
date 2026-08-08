"""Auto-generated regression test for tenant_feed."""

from tools.module_health import check_tenant_feed


def test_tenant_feed():
    """Verify tenant_feed imports, has routes, and has no exposure issues."""
    ok, msg = check_tenant_feed()
    assert ok, msg
