"""Auto-generated regression test for router."""

from tools.module_health import check_router


def test_router():
    """Verify router imports, has routes, and has no exposure issues."""
    ok, msg = check_router()
    assert ok, msg
