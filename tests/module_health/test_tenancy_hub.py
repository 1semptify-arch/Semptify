"""Auto-generated regression test for tenancy_hub."""

from tools.module_health import check_tenancy_hub


def test_tenancy_hub():
    """Verify tenancy_hub imports, has routes, and has no exposure issues."""
    ok, msg = check_tenancy_hub()
    assert ok, msg
