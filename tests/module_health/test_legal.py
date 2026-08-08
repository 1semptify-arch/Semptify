"""Auto-generated regression test for legal."""

from tools.module_health import check_legal


def test_legal():
    """Verify legal imports, has routes, and has no exposure issues."""
    ok, msg = check_legal()
    assert ok, msg
