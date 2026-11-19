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

    # Redis Cache & Efêmero (opcional, local)
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS Configuration (somente origens locais)
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://localhost:8081",
    ]
    CORS_ALLOW_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


settings = Settings()
