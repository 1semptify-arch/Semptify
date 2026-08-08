"""Auto-generated regression test for free_api."""

from tools.module_health import check_free_api


def test_free_api():
    """Verify free_api imports, has routes, and has no exposure issues."""
    ok, msg = check_free_api()
    assert ok, msg
