"""Auto-generated regression test for funding_search."""

from tools.module_health import check_funding_search


def test_funding_search():
    """Verify funding_search imports, has routes, and has no exposure issues."""
    ok, msg = check_funding_search()
    assert ok, msg
