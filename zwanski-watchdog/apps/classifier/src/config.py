"""Environment-backed settings for the classifier service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379"
    database_url: str = "postgresql://watchdog:watchdog@localhost:5432/watchdog"
    openrouter_api_key: str = ""
    openrouter_model: str = "mistralai/mixtral-8x7b-instruct"
    openrouter_fallback_model: str = "anthropic/claude-3-haiku"
    classifier_concurrency: int = 4
    internal_webhook_url: str | None = None


settings = Settings()
