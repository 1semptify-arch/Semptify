"""Auto-generated regression test for zoom_court."""

from tools.module_health import check_zoom_court


def test_zoom_court():
    """Verify zoom_court imports, has routes, and has no exposure issues."""
    ok, msg = check_zoom_court()
    assert ok, msg
