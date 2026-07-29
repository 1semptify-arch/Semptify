"""Auto-generated regression test for correspondence."""
from tools.module_health import check_correspondence


def test_correspondence():
    """Verify correspondence imports, has routes, and has no exposure issues."""
    ok, msg = check_correspondence()
    assert ok, msg
