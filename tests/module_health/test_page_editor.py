"""Auto-generated regression test for page_editor."""

from tools.module_health import check_page_editor


def test_page_editor():
    """Verify page_editor imports, has routes, and has no exposure issues."""
    ok, msg = check_page_editor()
    assert ok, msg
