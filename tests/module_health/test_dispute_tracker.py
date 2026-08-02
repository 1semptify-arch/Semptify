"""Auto-generated regression test for dispute_tracker."""

from tools.module_health import check_dispute_tracker


def test_dispute_tracker():
    """Verify dispute_tracker imports, has routes, and has no exposure issues."""
    ok, msg = check_dispute_tracker()
    assert ok, msg
