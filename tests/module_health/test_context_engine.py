"""Auto-generated regression test for context_engine."""

from tools.module_health import check_context_engine


def test_context_engine():
    """Verify context_engine imports, has routes, and has no exposure issues."""
    ok, msg = check_context_engine()
    assert ok, msg
