"""Auto-generated regression test for case_builder."""

from tools.module_health import check_case_builder


def test_case_builder():
    """Verify case_builder imports, has routes, and has no exposure issues."""
    ok, msg = check_case_builder()
    assert ok, msg
