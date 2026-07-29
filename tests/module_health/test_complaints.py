"""Auto-generated regression test for complaints."""

from tools.module_health import check_complaints


def test_complaints():
    """Verify complaints imports, has routes, and has no exposure issues."""
    ok, msg = check_complaints()
    assert ok, msg
