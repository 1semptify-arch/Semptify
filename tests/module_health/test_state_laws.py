"""Auto-generated regression test for state_laws."""

from tools.module_health import check_state_laws


def test_state_laws():
    """Verify state_laws imports, has routes, and has no exposure issues."""
    ok, msg = check_state_laws()
    assert ok, msg
