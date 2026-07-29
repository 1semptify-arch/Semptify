"""Auto-generated regression test for registry."""

from tools.module_health import check_registry


def test_registry():
    """Verify registry imports, has routes, and has no exposure issues."""
    ok, msg = check_registry()
    assert ok, msg
