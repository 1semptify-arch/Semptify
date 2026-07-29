"""Auto-generated regression test for crawler."""

from tools.module_health import check_crawler


def test_crawler():
    """Verify crawler imports, has routes, and has no exposure issues."""
    ok, msg = check_crawler()
    assert ok, msg
