"""Auto-generated regression test for law_library_page_router."""

from tools.module_health import check_law_library_page_router


def test_law_library_page_router():
    """Verify law_library_page_router imports, has routes, and has no exposure issues."""
    ok, msg = check_law_library_page_router()
    assert ok, msg
