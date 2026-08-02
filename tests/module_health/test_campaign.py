"""Auto-generated regression test for campaign."""

from tools.module_health import check_campaign


def test_campaign():
    """Verify campaign imports, has routes, and has no exposure issues."""
    ok, msg = check_campaign()
    assert ok, msg
