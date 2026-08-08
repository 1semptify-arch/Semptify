"""Auto-generated regression test for health."""

from tools.module_health import check_health


def test_health():
    """Verify health imports, has routes, and has no exposure issues."""
    ok, msg = check_health()
    assert ok, msg
