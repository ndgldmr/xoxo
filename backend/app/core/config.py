"""
Application configuration using Pydantic Settings.
Follows 12-factor app principles with environment-based configuration.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = Field(default="XOXO Education API", description="Application name")
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development", description="Runtime environment"
    )
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API version 1 prefix")

    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")

    # Database
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://xoxo:xoxo@localhost:5432/xoxo_dev",
        description="Async PostgreSQL database URL",
    )
    DB_ECHO: bool = Field(
        default=False, description="Echo SQL queries (useful for debugging)"
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(
        default=10, description="Max connections beyond pool size"
    )

    # CORS
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # Security (for future use with JWT)
    SECRET_KEY: str = Field(
        default="change-me-in-production-to-a-random-secret-key",
        description="Secret key for JWT encoding",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration time"
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def database_url_str(self) -> str:
        """Get database URL as string."""
        return str(self.DATABASE_URL)

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache ensures we only load settings once.
    """
    return Settings()


# Convenience export
settings = get_settings()
