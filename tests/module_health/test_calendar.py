"""Auto-generated regression test for calendar."""

from tools.module_health import check_calendar


def test_calendar():
    """Verify calendar imports, has routes, and has no exposure issues."""
    ok, msg = check_calendar()
    assert ok, msg
