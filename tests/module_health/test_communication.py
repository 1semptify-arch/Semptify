"""Auto-generated regression test for communication."""

from tools.module_health import check_communication


def test_communication():
    """Verify communication imports, has routes, and has no exposure issues."""
    ok, msg = check_communication()
    assert ok, msg
