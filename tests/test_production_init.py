import os

from app.core.production_init import validate_production_mode


def test_validate_production_mode_requires_r2(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SECRET_KEY", "super-secret-key-1234567890")
    monkeypatch.setenv("HTTPS_ONLY", "true")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://localhost:8000")
    monkeypatch.setenv("DB_SSL_MODE", "require")
    monkeypatch.delenv("R2_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("R2_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("R2_BUCKET_NAME", raising=False)

    assert validate_production_mode() is False


def test_validate_production_mode_passes_with_r2(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SECRET_KEY", "super-secret-key-1234567890")
    monkeypatch.setenv("HTTPS_ONLY", "true")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://localhost:8000")
    monkeypatch.setenv("DB_SSL_MODE", "require")
    monkeypatch.setenv("R2_ACCOUNT_ID", "abc123")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key123")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret123")
    monkeypatch.setenv("R2_BUCKET_NAME", "semptify-system")

    assert validate_production_mode() is True
