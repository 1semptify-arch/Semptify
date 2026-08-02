"""Auto-generated regression test for core_system_core_router."""

from tools.module_health import check_core_system_core_router


def test_core_system_core_router():
    """Verify core_system_core_router imports, has routes, and has no exposure issues."""
    ok, msg = check_core_system_core_router()
    assert ok, msg
