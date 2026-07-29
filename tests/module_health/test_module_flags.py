"""Auto-generated regression test for module_flags."""

from tools.module_health import check_module_flags


def test_module_flags():
    """Verify module_flags imports, has routes, and has no exposure issues."""
    ok, msg = check_module_flags()
    assert ok, msg
