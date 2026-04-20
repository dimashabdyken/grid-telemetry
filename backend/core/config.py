"""Application settings loaded from environment variables via pydantic-settings."""

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

    # OpenF1
    OPENF1_BASE_URL: str = "https://api.openf1.org/v1"
    OPENF1_SESSION_KEY: str = "latest"
    OPENF1_POLL_INTERVAL: float = 0.27

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
