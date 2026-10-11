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
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./study_reviewer.db"
    SECRET_KEY: str = "super-secret-key-study-reviewer-32b-length!"  # noqa: S105
    HOST: str = "0.0.0.0"  # noqa: S104
    PORT: int = 8000

    # Google OAuth 2.0 / OIDC
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # Google Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # Redis Cache & Efêmero
    REDIS_URL: str = "redis://localhost:6379/0"

    # Backend de Eventos de Estudo: 'postgres' ou 'dynamodb'
    STUDY_EVENTS_BACKEND: str = "postgres"
    DYNAMODB_TABLE_STUDY_EVENTS: str = "study_events"
    AWS_REGION: str = "us-east-1"
    DYNAMODB_ENDPOINT_URL: str | None = None
    DYNAMODB_TTL_DAYS: int = 90

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://localhost:8081",
        "http://10.0.2.2:8000",
    ]
    CORS_ALLOW_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1|10\.0\.2\.2)(:\d+)?$"


settings = Settings()
