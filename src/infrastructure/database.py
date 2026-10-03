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


def get_engine_args(url: str) -> dict[str, Any]:
    """Retorna argumentos de conexão adequados para o dialeto do banco de dados."""
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(settings.DATABASE_URL, **get_engine_args(settings.DATABASE_URL))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session]:
    """Dependência para obtenção de sessão de banco de dados com fechamento garantido."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
