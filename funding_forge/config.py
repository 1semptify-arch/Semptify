"""Funding Forge configuration."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FundingForgeSettings(BaseSettings):
    """Environment-driven settings for the standalone funding app."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./funding_forge.db"
    uploads_dir: str = "funding_forge/uploads"
    app_host: str = "127.0.0.1"
    app_port: int = 8001
    debug: bool = False

    # Admin credentials. Accepts Funding Forge prefixed env vars or the same
    # ADMIN_* variables used by the main Semptify app.
    admin_username: str = Field(
        default="",
        validation_alias=AliasChoices("FUNDING_FORGE_ADMIN_USERNAME", "ADMIN_USERNAME"),
    )
    admin_password: str = Field(
        default="",
        validation_alias=AliasChoices("FUNDING_FORGE_ADMIN_PASSWORD", "ADMIN_PASSWORD"),
    )
    admin_totp_secret: str = Field(
        default="",
        validation_alias=AliasChoices("FUNDING_FORGE_ADMIN_TOTP_SECRET", "ADMIN_TOTP_SECRET"),
    )

    # Storage backend: local or r2.
    storage_backend: str = Field(
        default="local",
        validation_alias=AliasChoices("FUNDING_FORGE_STORAGE_BACKEND", "STORAGE_BACKEND"),
    )

    # Cloudflare R2 credentials for persistent system storage.
    r2_account_id: str = Field(
        default="",
        validation_alias=AliasChoices("FUNDING_FORGE_R2_ACCOUNT_ID", "R2_ACCOUNT_ID"),
    )
    r2_access_key_id: str = Field(
        default="",
        validation_alias=AliasChoices("FUNDING_FORGE_R2_ACCESS_KEY_ID", "R2_ACCESS_KEY_ID"),
    )
    r2_secret_access_key: str = Field(
        default="",
        validation_alias=AliasChoices("FUNDING_FORGE_R2_SECRET_ACCESS_KEY", "R2_SECRET_ACCESS_KEY"),
    )
    r2_bucket_name: str = Field(
        default="",
        validation_alias=AliasChoices("FUNDING_FORGE_R2_BUCKET_NAME", "R2_BUCKET_NAME"),
    )
    r2_endpoint_url: str = Field(
        default="",
        validation_alias=AliasChoices("FUNDING_FORGE_R2_ENDPOINT_URL", "R2_ENDPOINT_URL"),
    )

    @property
    def auth_enabled(self) -> bool:
        """Admin authentication is active when a username and password are set."""
        return bool(self.admin_username and self.admin_password)

    @property
    def r2_configured(self) -> bool:
        """True when all required R2 credentials are present."""
        return bool(self.r2_account_id and self.r2_access_key_id and self.r2_secret_access_key and self.r2_bucket_name)


settings = FundingForgeSettings()
