"""Auto-generated regression test for role_upgrade."""

from tools.module_health import check_role_upgrade


def test_role_upgrade():
    """Verify role_upgrade imports, has routes, and has no exposure issues."""
    ok, msg = check_role_upgrade()
    assert ok, msg
