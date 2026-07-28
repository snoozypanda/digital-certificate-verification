"""
Application configuration module.

Uses pydantic-settings to load configuration from environment variables
and .env file. Settings are cached via lru_cache for performance.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/certificates_db"

    # Application
    app_name: str = "Certificate Verification System"
    app_version: str = "1.0.0"
    base_url: str = "http://10.1.10.35:8000"

    # File Storage
    static_dir: str = "static"
    upload_dir: str = "uploads"

    @property
    def certificates_dir(self) -> str:
        return f"{self.static_dir}/certificates"

    @property
    def qr_codes_dir(self) -> str:
        return f"{self.static_dir}/qr_codes"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using lru_cache ensures the .env file is read only once,
    and the same Settings object is reused across the application.
    """
    return Settings()
