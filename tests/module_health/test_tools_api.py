"""Auto-generated regression test for tools_api."""

from tools.module_health import check_tools_api


def test_tools_api():
    """Verify tools_api imports, has routes, and has no exposure issues."""
    ok, msg = check_tools_api()
    assert ok, msg
