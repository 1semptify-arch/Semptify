"""Auto-generated regression test for litigation_intelligence_lis_router."""

from tools.module_health import check_litigation_intelligence_lis_router


def test_litigation_intelligence_lis_router():
    """Verify litigation_intelligence_lis_router imports, has routes, and has no exposure issues."""
    ok, msg = check_litigation_intelligence_lis_router()
    assert ok, msg
