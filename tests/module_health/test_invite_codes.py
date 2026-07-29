"""Auto-generated regression test for invite_codes."""

from tools.module_health import check_invite_codes


def test_invite_codes():
    """Verify invite_codes imports, has routes, and has no exposure issues."""
    ok, msg = check_invite_codes()
    assert ok, msg
