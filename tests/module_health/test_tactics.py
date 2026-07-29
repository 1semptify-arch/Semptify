"""Auto-generated regression test for tactics."""

from tools.module_health import check_tactics


def test_tactics():
    """Verify tactics imports, has routes, and has no exposure issues."""
    ok, msg = check_tactics()
    assert ok, msg
