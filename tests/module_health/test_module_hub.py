"""Auto-generated regression test for module_hub."""

from tools.module_health import check_module_hub


def test_module_hub():
    """Verify module_hub imports, has routes, and has no exposure issues."""
    ok, msg = check_module_hub()
    assert ok, msg
