"""Auto-generated regression test for ideas."""

from tools.module_health import check_ideas


def test_ideas():
    """Verify ideas imports, has routes, and has no exposure issues."""
    ok, msg = check_ideas()
    assert ok, msg
