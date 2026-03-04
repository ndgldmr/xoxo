"""Application configuration management."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    llm_api_key: str
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout: int = 30
    # Fallback model used when primary LLM is unavailable (same API key/base URL).
    # Set to empty string to disable the fallback LLM and go straight to hardcoded content.
    llm_fallback_model: str = "gemini-2.0-flash-lite"

    # WaSenderAPI Configuration
    wasender_api_key: str = ""
    wasender_webhook_secret: str = ""  # From WaSenderAPI dashboard → Webhook Secret

    # Database Configuration (optional - enables multi-recipient mode)
    database_url: str = ""  # e.g. "sqlite:///./xoxo.db"

    # API Authentication
    api_key: str = ""  # Required in production

    # GCP Cloud Scheduler (production-only; leave blank in local dev)
    gcp_project_id: str = ""
    gcp_location: str = ""          # e.g. "us-central1"
    gcp_scheduler_job_id: str = ""  # e.g. "xoxo-daily-send"
    service_url: str = ""           # Cloud Run URL, needed when updating the job's HTTP target URI

    # CORS
    allowed_origins: str = ""  # comma-separated, e.g. "https://xoxo.vercel.app,http://localhost:5173"

    # Application Settings
    dry_run: bool = True
    audit_log_path: str = "audit_log.jsonl"
    send_delay_seconds: float = 0.5  # Delay between sends in multi-recipient mode

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
