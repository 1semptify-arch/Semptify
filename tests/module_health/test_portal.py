"""Auto-generated regression test for portal."""

from tools.module_health import check_portal


def test_portal():
    """Verify portal imports, has routes, and has no exposure issues."""
    ok, msg = check_portal()
    assert ok, msg
