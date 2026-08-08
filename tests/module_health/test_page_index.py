"""Auto-generated regression test for page_index."""

from tools.module_health import check_page_index


def test_page_index():
    """Verify page_index imports, has routes, and has no exposure issues."""
    ok, msg = check_page_index()
    assert ok, msg
