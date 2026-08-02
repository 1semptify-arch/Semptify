"""Auto-generated regression test for hud_funding."""

from tools.module_health import check_hud_funding


def test_hud_funding():
    """Verify hud_funding imports, has routes, and has no exposure issues."""
    ok, msg = check_hud_funding()
    assert ok, msg
