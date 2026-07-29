"""Auto-generated regression test for judge."""

from tools.module_health import check_judge


def test_judge():
    """Verify judge imports, has routes, and has no exposure issues."""
    ok, msg = check_judge()
    assert ok, msg
