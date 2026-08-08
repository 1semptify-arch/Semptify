"""Auto-generated regression test for search."""

from tools.module_health import check_search


def test_search():
    """Verify search imports, has routes, and has no exposure issues."""
    ok, msg = check_search()
    assert ok, msg
