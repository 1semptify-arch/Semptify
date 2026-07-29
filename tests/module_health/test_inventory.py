"""Auto-generated regression test for inventory."""

from tools.module_health import check_inventory


def test_inventory():
    """Verify inventory imports, has routes, and has no exposure issues."""
    ok, msg = check_inventory()
    assert ok, msg
