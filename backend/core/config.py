"""Application settings loaded from environment variables via pydantic-settings."""

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # App
    APP_NAME: str = "Grid Telemetry"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 2

    # PostgreSQL
    POSTGRES_DSN: str = (
        "postgresql+asyncpg://grid:telemetry@localhost:5433/grid_telemetry"
    )

    # FastF1
    FASTF1_CACHE_DIR: str = "../../cache"
    FASTF1_DEFAULT_YEAR: int = 2023
    FASTF1_DEFAULT_EVENT: str = "Singapore"
    FASTF1_DEFAULT_SESSION: str = "R"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
    ]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        normalized = value.strip().lower()
        if normalized in {"release", "prod", "production"}:
            return False
        if normalized in {"debug", "dev", "development"}:
            return True

        return value


settings = Settings()
