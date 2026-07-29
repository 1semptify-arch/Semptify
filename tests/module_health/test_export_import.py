"""Auto-generated regression test for export_import."""

from tools.module_health import check_export_import


def test_export_import():
    """Verify export_import imports, has routes, and has no exposure issues."""
    ok, msg = check_export_import()
    assert ok, msg
