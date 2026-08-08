"""Auto-generated regression test for example_payment_tracking."""

from tools.module_health import check_example_payment_tracking


def test_example_payment_tracking():
    """Verify example_payment_tracking imports, has routes, and has no exposure issues."""
    ok, msg = check_example_payment_tracking()
    assert ok, msg
