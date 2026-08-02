"""Auto-generated regression test for versioning."""

from tools.module_health import check_versioning


def test_versioning():
    """Verify versioning imports, has routes, and has no exposure issues."""
    ok, msg = check_versioning()
    assert ok, msg
