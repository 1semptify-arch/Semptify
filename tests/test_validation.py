"""Tests for app.core.validation — input sanitization and validators."""

import pytest

from app.core.validation import (
    MAX_FORM_BODY_SIZE,
    MAX_JSON_BODY_SIZE,
    check_sql_injection,
    create_length_validator,
    normalize_whitespace,
    sanitize_filename,
    sanitize_for_search,
    sanitize_html,
    sanitize_path,
    strip_control_chars,
    validate_clean_string,
    validate_email,
    validate_no_html,
    validate_phone,
    validate_safe_filename,
    validate_safe_path,
    validate_uuid,
)

# ── sanitize_html ────────────────────────────────────────────────────────────


class TestSanitizeHtml:
    def test_escapes_angle_brackets(self):
        assert "&lt;script&gt;" in sanitize_html("<script>")

    def test_escapes_ampersand(self):
        assert "&amp;" in sanitize_html("foo & bar")

    def test_escapes_quotes(self):
        result = sanitize_html('"hello"')
        assert "&quot;" in result

    def test_empty_string_passthrough(self):
        assert sanitize_html("") == ""

    def test_plain_text_unchanged(self):
        assert sanitize_html("hello world") == "hello world"


# ── strip_control_chars ──────────────────────────────────────────────────────


class TestStripControlChars:
    def test_removes_null_byte(self):
        assert "\x00" not in strip_control_chars("ab\x00cd")

    def test_keeps_newline(self):
        assert strip_control_chars("a\nb") == "a\nb"

    def test_keeps_tab(self):
        assert strip_control_chars("a\tb") == "a\tb"

    def test_keeps_carriage_return(self):
        assert strip_control_chars("a\rb") == "a\rb"

    def test_removes_bell(self):
        assert "\x07" not in strip_control_chars("hello\x07world")

    def test_empty_string_passthrough(self):
        assert strip_control_chars("") == ""


# ── normalize_whitespace ─────────────────────────────────────────────────────


class TestNormalizeWhitespace:
    def test_collapses_spaces(self):
        assert normalize_whitespace("a   b") == "a b"

    def test_strips_leading_trailing(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_handles_mixed_whitespace(self):
        assert normalize_whitespace("a\t\n b") == "a b"

    def test_empty_string_passthrough(self):
        assert normalize_whitespace("") == ""


# ── sanitize_filename ────────────────────────────────────────────────────────


class TestSanitizeFilename:
    def test_removes_path_separators(self):
        result = sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result

    def test_removes_null_bytes(self):
        assert "\x00" not in sanitize_filename("file\x00.txt")

    def test_removes_special_chars(self):
        result = sanitize_filename('file<>:"|?*.txt')
        assert all(c not in result for c in '<>:"|?*')

    def test_truncates_to_255(self):
        long_name = "a" * 300
        assert len(sanitize_filename(long_name)) == 255

    def test_empty_string_passthrough(self):
        assert sanitize_filename("") == ""

    def test_normal_filename_unchanged(self):
        assert sanitize_filename("document.pdf") == "document.pdf"


# ── sanitize_path ────────────────────────────────────────────────────────────


class TestSanitizePath:
    def test_removes_traversal(self):
        result = sanitize_path("../../etc/passwd")
        assert ".." not in result

    def test_removes_null_bytes(self):
        assert "\x00" not in sanitize_path("path/\x00to/file")

    def test_normalizes_backslash(self):
        result = sanitize_path("path\\to\\file")
        assert "\\" not in result
        assert "/" in result

    def test_strips_leading_slash(self):
        result = sanitize_path("/absolute/path")
        assert not result.startswith("/")

    def test_empty_string_passthrough(self):
        assert sanitize_path("") == ""


# ── validate_email ───────────────────────────────────────────────────────────


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_lowercases(self):
        assert validate_email("USER@EXAMPLE.COM") == "user@example.com"

    def test_strips_whitespace(self):
        assert validate_email("  user@example.com  ") == "user@example.com"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            validate_email("not-an-email")

    def test_missing_at_raises(self):
        with pytest.raises(ValueError):
            validate_email("userexample.com")

    def test_missing_domain_raises(self):
        with pytest.raises(ValueError):
            validate_email("user@")


# ── validate_phone ───────────────────────────────────────────────────────────


class TestValidatePhone:
    def test_us_phone(self):
        result = validate_phone("(555) 123-4567")
        assert result == "5551234567"

    def test_with_country_code(self):
        result = validate_phone("+1 555-123-4567")
        assert result == "15551234567"

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="10-15 digits"):
            validate_phone("12345")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="10-15 digits"):
            validate_phone("1234567890123456")

    def test_empty_passthrough(self):
        assert validate_phone("") == ""


# ── validate_uuid ────────────────────────────────────────────────────────────


class TestValidateUuid:
    def test_valid_uuid(self):
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        assert validate_uuid(uuid) == uuid

    def test_uppercased_lowered(self):
        result = validate_uuid("550E8400-E29B-41D4-A716-446655440000")
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid UUID"):
            validate_uuid("not-a-uuid")


# ── check_sql_injection ─────────────────────────────────────────────────────


class TestCheckSqlInjection:
    def test_clean_text(self):
        assert check_sql_injection("hello world") is False

    def test_single_quote(self):
        assert check_sql_injection("'; DROP TABLE users;--") is True

    def test_sql_keyword(self):
        assert check_sql_injection("1 OR 1=1") is True

    def test_union_select(self):
        assert check_sql_injection("UNION SELECT * FROM users") is True

    def test_empty_string(self):
        assert check_sql_injection("") is False

    def test_double_dash_comment(self):
        assert check_sql_injection("admin--") is True


# ── sanitize_for_search ─────────────────────────────────────────────────────


class TestSanitizeForSearch:
    def test_removes_quotes(self):
        result = sanitize_for_search("it's a test")
        assert "'" not in result

    def test_removes_sql_keywords(self):
        result = sanitize_for_search("DROP table")
        assert "DROP" not in result

    def test_preserves_normal_text(self):
        result = sanitize_for_search("hello world")
        assert result == "hello world"

    def test_empty_passthrough(self):
        assert sanitize_for_search("") == ""


# ── create_length_validator ──────────────────────────────────────────────────


class TestCreateLengthValidator:
    def test_within_range(self):
        validator = create_length_validator(1, 10)
        assert validator("hello") == "hello"

    def test_too_short_raises(self):
        validator = create_length_validator(5, 10)
        with pytest.raises(ValueError, match="at least 5"):
            validator("hi")

    def test_too_long_raises(self):
        validator = create_length_validator(1, 5)
        with pytest.raises(ValueError, match="at most 5"):
            validator("toolongstring")


# ── pydantic validator wrappers ──────────────────────────────────────────────


class TestValidatorWrappers:
    def test_validate_no_html(self):
        assert "&lt;" in validate_no_html("<b>bold</b>")

    def test_validate_clean_string(self):
        result = validate_clean_string("hello\x00   world")
        assert result == "hello world"

    def test_validate_safe_filename(self):
        result = validate_safe_filename("../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result

    def test_validate_safe_path(self):
        result = validate_safe_path("../../etc/passwd")
        assert ".." not in result


# ── constants ────────────────────────────────────────────────────────────────


class TestConstants:
    def test_json_body_size(self):
        assert MAX_JSON_BODY_SIZE == 10 * 1024 * 1024

    def test_form_body_size(self):
        assert MAX_FORM_BODY_SIZE == 50 * 1024 * 1024
