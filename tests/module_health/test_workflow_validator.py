"""Auto-generated regression test for workflow_validator."""

from tools.module_health import check_workflow_validator


def test_workflow_validator():
    """Verify workflow_validator imports, has routes, and has no exposure issues."""
    ok, msg = check_workflow_validator()
    assert ok, msg
