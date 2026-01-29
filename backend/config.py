"""Application configuration."""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "CHM MediaHub"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://mediahub:mediahub@localhost:5432/mediahub"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT Auth
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # External Services
    chatbot_api_url: str = "http://localhost:8000"
    ops_console_api_url: str = "http://localhost:8015"

    # Webhook API key for ops-console sync
    webhook_api_key: str = "change-this-in-production"

    # Email (for invitations)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@chm-mediahub.com"

    # File storage
    upload_dir: str = "./uploads"
    reports_dir: str = "./reports"

    # CORS
    cors_origins: list[str] = ["http://localhost:3001", "http://127.0.0.1:3001"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
