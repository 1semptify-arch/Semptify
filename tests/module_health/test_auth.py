"""Auto-generated regression test for auth."""

from tools.module_health import check_auth


def test_auth():
    """Verify auth imports, has routes, and has no exposure issues."""
    ok, msg = check_auth()
    assert ok, msg
