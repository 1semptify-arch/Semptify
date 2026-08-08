"""Auto-generated regression test for run_modules."""

from tools.module_health import check_run_modules


def test_run_modules():
    """Verify run_modules imports, has routes, and has no exposure issues."""
    ok, msg = check_run_modules()
    assert ok, msg
