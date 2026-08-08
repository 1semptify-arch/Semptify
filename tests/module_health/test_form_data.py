"""Auto-generated regression test for form_data."""

from tools.module_health import check_form_data


def test_form_data():
    """Verify form_data imports, has routes, and has no exposure issues."""
    ok, msg = check_form_data()
    assert ok, msg
