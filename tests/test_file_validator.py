"""Tests for app.core.file_validator — file upload validation and security."""

import pytest

from app.core.file_validator import (
    FileValidationResult,
    FileValidator,
    file_validator,
    get_allowed_file_types,
    get_file_validator,
    validate_upload_file,
)


@pytest.fixture
def validator():
    return FileValidator()


# ── FileValidationResult ─────────────────────────────────────────────────────


class TestFileValidationResult:
    def test_defaults(self):
        r = FileValidationResult(is_valid=True)
        assert r.error_message is None
        assert r.file_type is None

    def test_invalid(self):
        r = FileValidationResult(is_valid=False, error_message="too big")
        assert not r.is_valid
        assert r.error_message == "too big"


# ── validate_file — extension checks ─────────────────────────────────────────


class TestValidateFileExtension:
    def test_blocked_extension(self, validator):
        result = validator.validate_file(b"content", "malware.exe", 100)
        assert not result.is_valid
        assert "not allowed" in result.error_message
        assert result.security_risk == "blocked_extension"

    def test_blocked_bat(self, validator):
        result = validator.validate_file(b"content", "run.bat", 100)
        assert not result.is_valid

    def test_blocked_sh(self, validator):
        result = validator.validate_file(b"content", "run.sh", 100)
        assert not result.is_valid

    def test_blocked_zip(self, validator):
        result = validator.validate_file(b"content", "archive.zip", 100)
        assert not result.is_valid

    def test_unsupported_extension(self, validator):
        result = validator.validate_file(b"content", "file.xyz", 100)
        assert not result.is_valid
        assert "not supported" in result.error_message


# ── validate_file — empty file ───────────────────────────────────────────────


class TestValidateFileEmpty:
    def test_empty_content(self, validator):
        result = validator.validate_file(b"", "doc.pdf", 0)
        assert not result.is_valid
        assert "empty" in result.error_message.lower()


# ── validate_file — size check ───────────────────────────────────────────────


class TestValidateFileSize:
    def test_oversized_txt(self, validator):
        huge = 11 * 1024 * 1024
        result = validator.validate_file(b"x", "note.txt", huge)
        assert not result.is_valid
        assert "exceeds" in result.error_message

    def test_within_limit(self, validator):
        content = b"hello world"
        result = validator.validate_file(content, "note.txt", len(content))
        assert result.is_valid


# ── validate_file — valid file ───────────────────────────────────────────────


class TestValidateFileValid:
    def test_valid_txt(self, validator):
        content = b"plain text"
        result = validator.validate_file(content, "readme.txt", len(content))
        assert result.is_valid
        assert result.file_type == "txt"
        assert result.file_size == len(content)

    def test_valid_csv(self, validator):
        content = b"a,b,c\n1,2,3"
        result = validator.validate_file(content, "data.csv", len(content))
        assert result.is_valid


# ── security checks ─────────────────────────────────────────────────────────


class TestSecurityChecks:
    def test_executable_signature_mz(self, validator):
        content = b"MZ\x90\x00" + b"\x00" * 100
        assert validator._has_executable_signature(content)

    def test_executable_signature_elf(self, validator):
        content = b"\x7fELF" + b"\x00" * 100
        assert validator._has_executable_signature(content)

    def test_no_executable_signature(self, validator):
        assert not validator._has_executable_signature(b"just text content")

    def test_script_content_detected(self, validator):
        assert validator._has_script_content(b"<script>alert(1)</script>")

    def test_script_powershell(self, validator):
        assert validator._has_script_content(b"powershell -exec bypass")

    def test_no_script_content(self, validator):
        assert not validator._has_script_content(b"normal document text")

    def test_suspicious_patterns(self, validator):
        assert validator._has_suspicious_patterns(b"base64_decode(data)")

    def test_no_suspicious_patterns(self, validator):
        assert not validator._has_suspicious_patterns(b"hello world")

    def test_macro_content(self, validator):
        assert validator._has_macro_content(b"something macros something")

    def test_no_macro_content(self, validator):
        assert not validator._has_macro_content(b"plain document")


# ── helper methods ───────────────────────────────────────────────────────────


class TestHelperMethods:
    def test_get_allowed_extensions(self, validator):
        extensions = validator.get_allowed_extensions()
        assert "pdf" in extensions
        assert "txt" in extensions
        assert "exe" not in extensions

    def test_get_file_type_info_known(self, validator):
        info = validator.get_file_type_info("pdf")
        assert info is not None
        assert info["description"] == "PDF document"

    def test_get_file_type_info_with_dot(self, validator):
        info = validator.get_file_type_info(".pdf")
        assert info is not None

    def test_get_file_type_info_unknown(self, validator):
        assert validator.get_file_type_info("xyz") is None

    def test_generate_file_hash(self, validator):
        h = validator.generate_file_hash(b"hello")
        assert isinstance(h, str)
        assert len(h) == 64

    def test_hash_deterministic(self, validator):
        a = validator.generate_file_hash(b"hello")
        b = validator.generate_file_hash(b"hello")
        assert a == b

    def test_hash_different_for_different_content(self, validator):
        a = validator.generate_file_hash(b"hello")
        b = validator.generate_file_hash(b"world")
        assert a != b


# ── sanitize_filename ────────────────────────────────────────────────────────


class TestSanitizeFilenameValidator:
    def test_removes_path_separators(self, validator):
        result = validator.sanitize_filename("../etc/passwd")
        assert "/" not in result
        assert "\\" not in result

    def test_strips_leading_dots(self, validator):
        result = validator.sanitize_filename("...hidden")
        assert not result.startswith(".")

    def test_empty_becomes_default(self, validator):
        result = validator.sanitize_filename("")
        assert result == "uploaded_file"

    def test_special_chars_only_becomes_default(self, validator):
        result = validator.sanitize_filename("!@#$%^&()")
        assert result == "uploaded_file"

    def test_length_limit(self, validator):
        result = validator.sanitize_filename("a" * 300 + ".pdf")
        assert len(result) <= 255


# ── module-level functions ───────────────────────────────────────────────────


class TestModuleFunctions:
    def test_get_file_validator_returns_instance(self):
        v = get_file_validator()
        assert isinstance(v, FileValidator)
        assert v is file_validator

    def test_validate_upload_file(self):
        result = validate_upload_file(b"text", "file.txt", 4)
        assert result.is_valid

    def test_get_allowed_file_types(self):
        types = get_allowed_file_types()
        assert "pdf" in types
        assert isinstance(types["pdf"], dict)
