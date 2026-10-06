"""Configuração de persistência e sessão com SQLAlchemy 2.0 (Camada 4 - Infraestrutura)."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.infrastructure.config import settings


class Base(DeclarativeBase):
    """Classe base declarativa para os modelos ORM."""


@event.listens_for(Engine, "connect")
def _setup_sqlite_functions(dbapi_connection: Any, connection_record: Any) -> None:
    """Configura funções personalizadas em conexões SQLite (ex: suporte a lower Unicode)."""
    if hasattr(dbapi_connection, "create_function"):
        dbapi_connection.create_function("lower", 1, str.lower)


def normalize_database_url(url: str) -> str:
    """Normaliza URLs de postgres/postgresql para postgresql+psycopg2."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def get_engine_args(url: str) -> dict[str, Any]:
    """Retorna argumentos de conexão adequados para o dialeto do banco de dados."""
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


db_url = normalize_database_url(settings.DATABASE_URL)
engine = create_engine(db_url, **get_engine_args(db_url))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session]:
    """Dependência para obtenção de sessão de banco de dados com fechamento garantido."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
