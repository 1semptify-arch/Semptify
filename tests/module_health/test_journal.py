"""Auto-generated regression test for journal."""

from tools.module_health import check_journal


def test_journal():
    """Verify journal imports, has routes, and has no exposure issues."""
    ok, msg = check_journal()
    assert ok, msg
