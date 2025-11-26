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

    # Security
    SECRET_KEY: str = Field(
        default="change-me-in-production-to-a-random-secret-key",
        description="Secret key for JWT encoding",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(
        default=10080,
        description="Refresh token expiration time in minutes (7 days default)",
    )

    # AI Configuration
    AI_PROVIDER: Literal["mock", "openai", "openrouter"] = Field(
        default="mock",
        description="AI provider for message generation (mock, openai, openrouter)",
    )
    AI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Model name for AI provider (e.g., gpt-4o-mini, gpt-3.5-turbo)",
    )
    AI_MAX_RETRIES: int = Field(
        default=1,
        description="Max retries for subject uniqueness conflicts during generation",
    )
    AI_TIMEOUT: float = Field(
        default=30.0, description="AI API request timeout in seconds"
    )
    AI_MAX_TOKENS: int = Field(
        default=500, description="Maximum tokens in AI response"
    )
    OPENAI_API_KEY: str | None = Field(
        default=None, description="OpenAI API key (required if AI_PROVIDER=openai)"
    )
    OPENROUTER_API_KEY: str | None = Field(
        default=None,
        description="OpenRouter API key (required if AI_PROVIDER=openrouter)",
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate SECRET_KEY is not using default in production."""
        # Access other fields via info.data
        environment = info.data.get("ENVIRONMENT", "development")
        if (
            environment == "production"
            and v == "change-me-in-production-to-a-random-secret-key"
        ):
            raise ValueError(
                "SECRET_KEY must be changed in production! "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v

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


def get_llm_client(settings: Settings):
    """
    Factory function to get the appropriate LLM client based on settings.

    Args:
        settings: Application settings instance

    Returns:
        LLMClient implementation (MockLLMClient, OpenAIClient, etc.)

    Raises:
        ValueError: If provider is not supported or required API key is missing
    """
    from app.core.llm_client import MockLLMClient, OpenAIClient

    provider = settings.AI_PROVIDER.lower()

    if provider == "mock":
        return MockLLMClient()

    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is required when AI_PROVIDER=openai. "
                "Set the environment variable or add it to .env"
            )
        return OpenAIClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.AI_MODEL,
            base_url="https://api.openai.com/v1",
            timeout=settings.AI_TIMEOUT,
            max_tokens=settings.AI_MAX_TOKENS,
        )

    elif provider == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY is required when AI_PROVIDER=openrouter. "
                "Set the environment variable or add it to .env"
            )
        return OpenAIClient(
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.AI_MODEL,
            base_url="https://openrouter.ai/api/v1",
            timeout=settings.AI_TIMEOUT,
            max_tokens=settings.AI_MAX_TOKENS,
        )

    else:
        raise ValueError(
            f"Unsupported AI provider: {provider}. "
            f"Supported providers: mock, openai, openrouter"
        )
