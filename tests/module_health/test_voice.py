"""Auto-generated regression test for voice."""

from tools.module_health import check_voice


def test_voice():
    """Verify voice imports, has routes, and has no exposure issues."""
    ok, msg = check_voice()
    assert ok, msg
