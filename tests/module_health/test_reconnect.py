"""Auto-generated regression test for reconnect."""

from tools.module_health import check_reconnect


def test_reconnect():
    """Verify reconnect imports, has routes, and has no exposure issues."""
    ok, msg = check_reconnect()
    assert ok, msg
