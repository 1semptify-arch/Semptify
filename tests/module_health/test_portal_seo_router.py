"""Auto-generated regression test for portal_seo_router."""

from tools.module_health import check_portal_seo_router


def test_portal_seo_router():
    """Verify portal_seo_router imports, has routes, and has no exposure issues."""
    ok, msg = check_portal_seo_router()
    assert ok, msg
