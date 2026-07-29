"""Auto-generated regression test for resource_directory."""

from tools.module_health import check_resource_directory


def test_resource_directory():
    """Verify resource_directory imports, has routes, and has no exposure issues."""
    ok, msg = check_resource_directory()
    assert ok, msg
