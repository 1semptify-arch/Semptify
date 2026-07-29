"""Auto-generated regression test for recognition."""

from tools.module_health import check_recognition


def test_recognition():
    """Verify recognition imports, has routes, and has no exposure issues."""
    ok, msg = check_recognition()
    assert ok, msg
