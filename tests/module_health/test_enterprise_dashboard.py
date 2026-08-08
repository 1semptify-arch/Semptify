"""Auto-generated regression test for enterprise_dashboard."""

from tools.module_health import check_enterprise_dashboard


def test_enterprise_dashboard():
    """Verify enterprise_dashboard imports, has routes, and has no exposure issues."""
    ok, msg = check_enterprise_dashboard()
    assert ok, msg
