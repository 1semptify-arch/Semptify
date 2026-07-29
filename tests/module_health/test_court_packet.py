"""Auto-generated regression test for court_packet."""

from tools.module_health import check_court_packet


def test_court_packet():
    """Verify court_packet imports, has routes, and has no exposure issues."""
    ok, msg = check_court_packet()
    assert ok, msg
