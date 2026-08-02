"""Auto-generated regression test for analytics."""

from tools.module_health import check_analytics


def test_analytics():
    """Verify analytics imports, has routes, and has no exposure issues."""
    ok, msg = check_analytics()
    assert ok, msg
