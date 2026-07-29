"""Auto-generated regression test for extraction."""

from tools.module_health import check_extraction


def test_extraction():
    """Verify extraction imports, has routes, and has no exposure issues."""
    ok, msg = check_extraction()
    assert ok, msg
