"""Auto-generated regression test for dev_lab."""

from tools.module_health import check_dev_lab


def test_dev_lab():
    """Verify dev_lab imports, has routes, and has no exposure issues."""
    ok, msg = check_dev_lab()
    assert ok, msg
