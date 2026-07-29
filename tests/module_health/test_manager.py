"""Auto-generated regression test for manager."""

from tools.module_health import check_manager


def test_manager():
    """Verify manager imports, has routes, and has no exposure issues."""
    ok, msg = check_manager()
    assert ok, msg
