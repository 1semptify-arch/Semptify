"""Auto-generated regression test for unified_overlays."""

from tools.module_health import check_unified_overlays


def test_unified_overlays():
    """Verify unified_overlays imports, has routes, and has no exposure issues."""
    ok, msg = check_unified_overlays()
    assert ok, msg
