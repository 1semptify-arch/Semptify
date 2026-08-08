"""Auto-generated regression test for development."""

from tools.module_health import check_development


def test_development():
    """Verify development imports, has routes, and has no exposure issues."""
    ok, msg = check_development()
    assert ok, msg
