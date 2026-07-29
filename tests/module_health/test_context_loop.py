"""Auto-generated regression test for context_loop."""

from tools.module_health import check_context_loop


def test_context_loop():
    """Verify context_loop imports, has routes, and has no exposure issues."""
    ok, msg = check_context_loop()
    assert ok, msg
