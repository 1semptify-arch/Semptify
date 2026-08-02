"""Auto-generated regression test for fraud_exposure."""

from tools.module_health import check_fraud_exposure


def test_fraud_exposure():
    """Verify fraud_exposure imports, has routes, and has no exposure issues."""
    ok, msg = check_fraud_exposure()
    assert ok, msg
