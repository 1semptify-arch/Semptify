"""Auto-generated regression test for storage."""

from tools.module_health import check_storage


def test_storage():
    """Verify storage imports, has routes, and has no exposure issues."""
    ok, msg = check_storage()
    assert ok, msg
