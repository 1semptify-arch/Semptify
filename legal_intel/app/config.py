# app/config.py
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from legal_intel directory explicitly
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path, override=True)

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://semptify:semptify@localhost:5432/legal_intel"

    class Config:
        env_file = str(env_path)
        env_file_encoding = "utf-8"

settings = Settings()
