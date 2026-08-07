"""Tests for app.core.utc — UTC datetime utilities."""

from datetime import UTC, datetime, timedelta, timezone

from app.core.utc import parse_iso, to_utc, utc_now, utc_now_iso


class TestUtcNow:
    def test_returns_datetime(self):
        result = utc_now()
        assert isinstance(result, datetime)

    def test_timezone_aware(self):
        result = utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_close_to_real_time(self):
        before = datetime.now(UTC)
        result = utc_now()
        after = datetime.now(UTC)
        assert before <= result <= after


class TestUtcNowIso:
    def test_returns_string(self):
        result = utc_now_iso()
        assert isinstance(result, str)

    def test_ends_with_z(self):
        result = utc_now_iso()
        assert result.endswith("Z")

    def test_no_offset_suffix(self):
        result = utc_now_iso()
        assert "+00:00" not in result

    def test_parseable(self):
        result = utc_now_iso()
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None


class TestToUtc:
    def test_naive_assumes_utc(self):
        naive = datetime(2025, 6, 1, 12, 0, 0)  # noqa: DTZ001
        result = to_utc(naive)
        assert result.tzinfo == UTC
        assert result.year == 2025
        assert result.hour == 12

    def test_aware_utc_passthrough(self):
        aware = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
        result = to_utc(aware)
        assert result == aware

    def test_aware_non_utc_converts(self):
        eastern = timezone(timedelta(hours=-5))
        aware = datetime(2025, 6, 1, 12, 0, 0, tzinfo=eastern)
        result = to_utc(aware)
        assert result.tzinfo == UTC
        assert result.hour == 17


class TestParseIso:
    def test_z_suffix(self):
        result = parse_iso("2025-12-08T03:00:00Z")
        assert result.tzinfo == UTC
        assert result.hour == 3

    def test_offset_suffix(self):
        result = parse_iso("2025-12-08T03:00:00+00:00")
        assert result.tzinfo == UTC
        assert result.hour == 3

    def test_naive_string_assumes_utc(self):
        result = parse_iso("2025-12-08T03:00:00")
        assert result.tzinfo == UTC

    def test_non_utc_offset_converts(self):
        result = parse_iso("2025-12-08T03:00:00-05:00")
        assert result.tzinfo == UTC
        assert result.hour == 8

    def test_roundtrip(self):
        iso = utc_now_iso()
        parsed = parse_iso(iso)
        assert parsed.tzinfo == UTC
