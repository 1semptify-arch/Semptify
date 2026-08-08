"""Auto-generated regression test for public_exposure."""

from tools.module_health import check_public_exposure


def test_public_exposure():
    """Verify public_exposure imports, has routes, and has no exposure issues."""
    ok, msg = check_public_exposure()
    assert ok, msg
