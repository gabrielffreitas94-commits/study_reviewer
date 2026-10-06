"""Configurações da aplicação via variáveis de ambiente (Pydantic Settings)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais da aplicação."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Study Reviewer"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./study_reviewer.db"
    SECRET_KEY: str = "super-secret-key-study-reviewer-32b-length!"  # noqa: S105
    HOST: str = "0.0.0.0"  # noqa: S104
    PORT: int = 8000

    # Google OAuth 2.0 / OIDC
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # Redis Cache & Efêmero
    REDIS_URL: str = "redis://localhost:6379/0"

    # Backend de Eventos de Estudo: 'postgres' ou 'dynamodb'
    STUDY_EVENTS_BACKEND: str = "postgres"
    DYNAMODB_TABLE_STUDY_EVENTS: str = "study_events"
    AWS_REGION: str = "us-east-1"
    DYNAMODB_ENDPOINT_URL: str | None = None
    DYNAMODB_TTL_DAYS: int = 90


settings = Settings()
