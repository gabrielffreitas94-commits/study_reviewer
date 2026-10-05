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
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    # Redis Cache & Efêmero
    REDIS_URL: str = "redis://localhost:6379/0"


settings = Settings()
