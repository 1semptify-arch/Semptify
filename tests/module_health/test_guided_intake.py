"""Auto-generated regression test for guided_intake."""

from tools.module_health import check_guided_intake


def test_guided_intake():
    """Verify guided_intake imports, has routes, and has no exposure issues."""
    ok, msg = check_guided_intake()
    assert ok, msg
