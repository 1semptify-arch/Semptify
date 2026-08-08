"""Auto-generated regression test for cloud_sync."""

from tools.module_health import check_cloud_sync


def test_cloud_sync():
    """Verify cloud_sync imports, has routes, and has no exposure issues."""
    ok, msg = check_cloud_sync()
    assert ok, msg
