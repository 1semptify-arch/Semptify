"""Auto-generated regression test for filedored."""
from tools.module_health import check_filedored


def test_filedored():
    """Verify filedored imports, has routes, and has no exposure issues."""
    ok, msg = check_filedored()
    assert ok, msg
