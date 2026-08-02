"""Auto-generated regression test for intake."""

from tools.module_health import check_intake


def test_intake():
    """Verify intake imports, has routes, and has no exposure issues."""
    ok, msg = check_intake()
    assert ok, msg
