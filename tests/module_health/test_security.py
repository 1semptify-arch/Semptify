"""Auto-generated regression test for security."""

from tools.module_health import check_security


def test_security():
    """Verify security imports, has routes, and has no exposure issues."""
    ok, msg = check_security()
    assert ok, msg
