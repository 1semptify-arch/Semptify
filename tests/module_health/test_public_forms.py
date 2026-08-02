"""Auto-generated regression test for public_forms."""

from tools.module_health import check_public_forms


def test_public_forms():
    """Verify public_forms imports, has routes, and has no exposure issues."""
    ok, msg = check_public_forms()
    assert ok, msg
