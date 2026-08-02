"""Auto-generated regression test for briefcase."""

from tools.module_health import check_briefcase


def test_briefcase():
    """Verify briefcase imports, has routes, and has no exposure issues."""
    ok, msg = check_briefcase()
    assert ok, msg
