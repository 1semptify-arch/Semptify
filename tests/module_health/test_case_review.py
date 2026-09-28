"""Auto-generated regression test for case_review."""

from tools.module_health import check_case_review


def test_case_review():
    """Verify case_review imports, has routes, and has no exposure issues."""
    ok, msg = check_case_review()
    assert ok, msg
