"""Auto-generated regression test for court_forms."""

from tools.module_health import check_court_forms


def test_court_forms():
    """Verify court_forms imports, has routes, and has no exposure issues."""
    ok, msg = check_court_forms()
    assert ok, msg
