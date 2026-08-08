"""Auto-generated regression test for testing."""

from tools.module_health import check_testing


def test_testing():
    """Verify testing imports, has routes, and has no exposure issues."""
    ok, msg = check_testing()
    assert ok, msg
