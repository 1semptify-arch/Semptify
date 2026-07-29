"""Auto-generated regression test for eviction_defense."""

from tools.module_health import check_eviction_defense


def test_eviction_defense():
    """Verify eviction_defense imports, has routes, and has no exposure issues."""
    ok, msg = check_eviction_defense()
    assert ok, msg
