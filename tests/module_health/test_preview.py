"""Auto-generated regression test for preview."""

from tools.module_health import check_preview


def test_preview():
    """Verify preview imports, has routes, and has no exposure issues."""
    ok, msg = check_preview()
    assert ok, msg
