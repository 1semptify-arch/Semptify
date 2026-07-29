"""Auto-generated regression test for user."""

from tools.module_health import check_user


def test_user():
    """Verify user imports, has routes, and has no exposure issues."""
    ok, msg = check_user()
    assert ok, msg
