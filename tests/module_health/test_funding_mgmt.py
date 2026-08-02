"""Auto-generated regression test for funding_mgmt."""

from tools.module_health import check_funding_mgmt


def test_funding_mgmt():
    """Verify funding_mgmt imports, has routes, and has no exposure issues."""
    ok, msg = check_funding_mgmt()
    assert ok, msg
