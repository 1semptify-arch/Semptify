"""Auto-generated regression test for vault."""

from tools.module_health import check_vault


def test_vault():
    """Verify vault imports, has routes, and has no exposure issues."""
    ok, msg = check_vault()
    assert ok, msg
