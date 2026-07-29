"""Auto-generated regression test for ui_composer."""

from tools.module_health import check_ui_composer


def test_ui_composer():
    """Verify ui_composer imports, has routes, and has no exposure issues."""
    ok, msg = check_ui_composer()
    assert ok, msg
