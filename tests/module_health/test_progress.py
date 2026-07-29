"""Auto-generated regression test for progress."""

from tools.module_health import check_progress


def test_progress():
    """Verify progress imports, has routes, and has no exposure issues."""
    ok, msg = check_progress()
    assert ok, msg
