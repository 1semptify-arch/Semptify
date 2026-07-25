"""Funding Forge configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class FundingForgeSettings(BaseSettings):
    """Environment-driven settings for the standalone funding app."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    funding_forge_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./funding_forge.db"
    uploads_dir: str = "funding_forge/uploads"
    app_host: str = "127.0.0.1"
    app_port: int = 8001
    debug: bool = False

    @property
    def auth_enabled(self) -> bool:
        """The workspace key gate is active only when a key is configured."""
        return bool(self.funding_forge_key)


settings = FundingForgeSettings()
