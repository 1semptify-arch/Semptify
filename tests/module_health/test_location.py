"""Auto-generated regression test for location."""

from tools.module_health import check_location


def test_location():
    """Verify location imports, has routes, and has no exposure issues."""
    ok, msg = check_location()
    assert ok, msg
