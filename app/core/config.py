"""
Semptify Configuration
Settings loaded from environment variables with secure defaults.
Set SECURITY_MODE=enforced in production. See .env.example for all options.
"""

import logging
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load .env before any os.getenv() calls (Settings class attributes are evaluated at import time)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env", override=True)

_WEAK_KEY = "change-me-in-production-use-secrets"
logger = logging.getLogger(__name__)


def _resolve_secret_key() -> str:
    """Return SECRET_KEY from env, or generate a secure random key with a warning."""
    key = os.getenv("SECRET_KEY", "")
    security_mode = os.getenv("SECURITY_MODE", "open").lower()
    if not key or key == _WEAK_KEY:
        if security_mode == "enforced":
            raise ValueError(
                "SECRET_KEY must be configured for document registry integrity when SECURITY_MODE=enforced."
            )
        generated = secrets.token_urlsafe(64)
        logger.warning(
            "SECRET_KEY not set or uses the insecure default. "
            "A temporary key has been generated for this session. "
            "Set SECRET_KEY in your .env file for production: SECRET_KEY=%s",
            generated,
        )
        return generated
    return key


def _resolve_database_url() -> str:
    """Return DATABASE_URL, converting postgres:// / postgresql:// to the asyncpg driver."""
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./semptify.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite://") and "+aiosqlite" not in url:
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


class Settings:
    app_name: str = "Semptify"
    app_version: str = "5.0.0"
    app_description: str = "Semptify - Tenant Rights Protection Platform"
    debug: bool = False
    enable_docs: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    # open = no auth (dev/testing); enforced = storage OAuth required (production)
    security_mode: Literal["open", "enforced"] = os.getenv("SECURITY_MODE", "open")
    secret_key: str = _resolve_secret_key()
    database_url: str = _resolve_database_url()
    upload_dir: str = "uploads"
    vault_dir: str = "uploads/vault"
    max_upload_size_mb: int = 50
    allowed_extensions: str = "pdf,png,jpg,jpeg,gif,doc,docx,txt,mp3,mp4,wav"
    ai_provider: Literal["openai", "azure", "ollama", "groq", "anthropic", "gemini", "none"] = "anthropic"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_json_format: bool = os.getenv("LOG_JSON_FORMAT", "False").lower() in ("1", "true", "yes", "on")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    @property
    def cors_origins_list(self):
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    google_ai_api_key: str = os.getenv("GOOGLE_AI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # OAuth storage config
    google_drive_client_id: str = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "")
    google_drive_client_secret: str = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "")
    dropbox_app_key: str = os.getenv("DROPBOX_APP_KEY", "")
    dropbox_app_secret: str = os.getenv("DROPBOX_APP_SECRET", "")
    onedrive_client_id: str = os.getenv("ONEDRIVE_CLIENT_ID", "")
    onedrive_client_secret: str = os.getenv("ONEDRIVE_CLIENT_SECRET", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_ai_endpoint: str = os.getenv("AZURE_AI_ENDPOINT", "")
    azure_ai_key1: str = os.getenv("AZURE_AI_KEY1", "")
    azure_ai_key2: str = os.getenv("AZURE_AI_KEY2", "")
    azure_ai_region: str = os.getenv("AZURE_AI_REGION", "eastus")
    github_token: str = os.getenv("GITHUB_TOKEN", "")

    @classmethod
    def get_settings(cls):
        return cls()


@lru_cache()
def get_settings() -> Settings:
    return Settings.get_settings()
