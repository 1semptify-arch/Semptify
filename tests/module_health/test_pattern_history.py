"""Auto-generated regression test for pattern_history."""

from tools.module_health import check_pattern_history


def test_pattern_history():
    """Verify pattern_history imports, has routes, and has no exposure issues."""
    ok, msg = check_pattern_history()
    assert ok, msg
