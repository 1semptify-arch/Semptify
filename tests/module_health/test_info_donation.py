"""Auto-generated regression test for info_donation."""

from tools.module_health import check_info_donation


def test_info_donation():
    """Verify info_donation imports, has routes, and has no exposure issues."""
    ok, msg = check_info_donation()
    assert ok, msg
