"""Auto-generated regression test for workflow."""

from tools.module_health import check_workflow


def test_workflow():
    """Verify workflow imports, has routes, and has no exposure issues."""
    ok, msg = check_workflow()
    assert ok, msg
