"""Auto-generated regression test for law_linker."""
from tools.module_health import check_law_linker


def test_law_linker():
    """Verify law_linker imports, has routes, and has no exposure issues."""
    ok, msg = check_law_linker()
    assert ok, msg
