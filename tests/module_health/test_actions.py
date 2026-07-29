"""Auto-generated regression test for actions."""

from tools.module_health import check_actions


def test_actions():
    """Verify actions imports, has routes, and has no exposure issues."""
    ok, msg = check_actions()
    assert ok, msg
