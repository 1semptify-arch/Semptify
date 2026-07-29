"""Auto-generated regression test for vault_engine."""

from tools.module_health import check_vault_engine


def test_vault_engine():
    """Verify vault_engine imports, has routes, and has no exposure issues."""
    ok, msg = check_vault_engine()
    assert ok, msg
