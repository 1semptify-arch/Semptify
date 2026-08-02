"""Auto-generated regression test for routes."""

from tools.module_health import check_routes


def test_routes():
    """Verify routes imports, has routes, and has no exposure issues."""
    ok, msg = check_routes()
    assert ok, msg
