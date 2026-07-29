"""Auto-generated regression test for functionx."""

from tools.module_health import check_functionx


def test_functionx():
    """Verify functionx imports, has routes, and has no exposure issues."""
    ok, msg = check_functionx()
    assert ok, msg
