"""Auto-generated regression test for zoom_court_prep."""

from tools.module_health import check_zoom_court_prep


def test_zoom_court_prep():
    """Verify zoom_court_prep imports, has routes, and has no exposure issues."""
    ok, msg = check_zoom_court_prep()
    assert ok, msg
