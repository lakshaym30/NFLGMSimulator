from datetime import datetime
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    project_name: str = Field(default="Cardinals GM Simulator API")
    version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    commit_sha: str = Field(default="local-dev")

    database_url: str = Field(default="sqlite:///./nfl.db")
    salary_cap_limit: float = Field(default=255_400_000)
    cap_year: int = Field(default_factory=lambda: datetime.utcnow().year)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


settings = get_settings()
