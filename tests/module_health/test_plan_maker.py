"""Auto-generated regression test for plan_maker."""

from tools.module_health import check_plan_maker


def test_plan_maker():
    """Verify plan_maker imports, has routes, and has no exposure issues."""
    ok, msg = check_plan_maker()
    assert ok, msg
