"""Auto-generated regression test for user_concerns."""
from tools.module_health import check_user_concerns


def test_user_concerns():
    """Verify user_concerns imports, has routes, and has no exposure issues."""
    ok, msg = check_user_concerns()
    assert ok, msg
