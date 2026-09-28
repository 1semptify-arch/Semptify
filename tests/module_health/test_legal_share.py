"""Auto-generated regression test for legal_share."""

from tools.module_health import check_legal_share


def test_legal_share():
    """Verify legal_share imports, has routes, and has no exposure issues."""
    ok, msg = check_legal_share()
    assert ok, msg
