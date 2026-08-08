"""Auto-generated regression test for packet_builder."""

from tools.module_health import check_packet_builder


def test_packet_builder():
    """Verify packet_builder imports, has routes, and has no exposure issues."""
    ok, msg = check_packet_builder()
    assert ok, msg
