"""Auto-generated regression test for websocket."""

from tools.module_health import check_websocket


def test_websocket():
    """Verify websocket imports, has routes, and has no exposure issues."""
    ok, msg = check_websocket()
    assert ok, msg
