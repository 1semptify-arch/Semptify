"""Auto-generated regression test for timeline."""

from tools.module_health import check_timeline


def test_timeline():
    """Verify timeline imports, has routes, and has no exposure issues."""
    ok, msg = check_timeline()
    assert ok, msg
