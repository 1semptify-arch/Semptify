"""Auto-generated regression test for capabilities."""

from tools.module_health import check_capabilities


def test_capabilities():
    """Verify capabilities imports, has routes, and has no exposure issues."""
    ok, msg = check_capabilities()
    assert ok, msg
