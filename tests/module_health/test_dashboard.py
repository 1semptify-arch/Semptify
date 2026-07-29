"""Auto-generated regression test for dashboard."""

from tools.module_health import check_dashboard


def test_dashboard():
    """Verify dashboard imports, has routes, and has no exposure issues."""
    ok, msg = check_dashboard()
    assert ok, msg
