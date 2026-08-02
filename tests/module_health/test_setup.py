"""Auto-generated regression test for setup."""

from tools.module_health import check_setup


def test_setup():
    """Verify setup imports, has routes, and has no exposure issues."""
    ok, msg = check_setup()
    assert ok, msg
