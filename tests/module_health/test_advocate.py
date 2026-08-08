"""Auto-generated regression test for advocate."""

from tools.module_health import check_advocate


def test_advocate():
    """Verify advocate imports, has routes, and has no exposure issues."""
    ok, msg = check_advocate()
    assert ok, msg
