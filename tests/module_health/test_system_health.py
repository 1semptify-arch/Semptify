"""Auto-generated regression test for system_health."""

from tools.module_health import check_system_health


def test_system_health():
    """Verify system_health imports, has routes, and has no exposure issues."""
    ok, msg = check_system_health()
    assert ok, msg
