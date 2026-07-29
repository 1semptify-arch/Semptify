"""Auto-generated regression test for mndes."""

from tools.module_health import check_mndes


def test_mndes():
    """Verify mndes imports, has routes, and has no exposure issues."""
    ok, msg = check_mndes()
    assert ok, msg
