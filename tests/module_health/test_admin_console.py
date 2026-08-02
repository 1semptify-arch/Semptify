"""Auto-generated regression test for admin_console."""

from tools.module_health import check_admin_console


def test_admin_console():
    """Verify admin_console imports, has routes, and has no exposure issues."""
    ok, msg = check_admin_console()
    assert ok, msg
