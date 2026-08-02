"""Auto-generated regression test for legal_trails."""

from tools.module_health import check_legal_trails


def test_legal_trails():
    """Verify legal_trails imports, has routes, and has no exposure issues."""
    ok, msg = check_legal_trails()
    assert ok, msg
