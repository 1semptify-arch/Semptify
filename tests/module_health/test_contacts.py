"""Auto-generated regression test for contacts."""

from tools.module_health import check_contacts


def test_contacts():
    """Verify contacts imports, has routes, and has no exposure issues."""
    ok, msg = check_contacts()
    assert ok, msg
