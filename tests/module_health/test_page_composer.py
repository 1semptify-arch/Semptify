"""Auto-generated regression test for page_composer."""

from tools.module_health import check_page_composer


def test_page_composer():
    """Verify page_composer imports, has routes, and has no exposure issues."""
    ok, msg = check_page_composer()
    assert ok, msg
