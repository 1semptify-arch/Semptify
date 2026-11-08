"""Auto-generated regression test for executive_admin."""

from tools.module_health import check_executive_admin


def test_executive_admin():
    """Verify executive_admin imports, has routes, and has no exposure issues."""
    ok, msg = check_executive_admin()
    assert ok, msg
