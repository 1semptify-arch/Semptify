"""Auto-generated regression test for role_ui."""

from tools.module_health import check_role_ui


def test_role_ui():
    """Verify role_ui imports, has routes, and has no exposure issues."""
    ok, msg = check_role_ui()
    assert ok, msg
