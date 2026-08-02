"""Auto-generated regression test for data_freshness."""

from tools.module_health import check_data_freshness


def test_data_freshness():
    """Verify data_freshness imports, has routes, and has no exposure issues."""
    ok, msg = check_data_freshness()
    assert ok, msg
