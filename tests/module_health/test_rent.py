"""Auto-generated regression test for rent."""

from tools.module_health import check_rent


def test_rent():
    """Verify rent imports, has routes, and has no exposure issues."""
    ok, msg = check_rent()
    assert ok, msg
