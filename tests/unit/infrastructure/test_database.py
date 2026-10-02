"""Testes unitários para a configuração de banco de dados (Camada 4 - Infraestrutura)."""

import pytest

from src.infrastructure.database import get_db, get_engine_args


@pytest.mark.unit
def test_get_engine_args_sqlite() -> None:
    """Verifica argumentos de conexão para banco SQLite."""
    args = get_engine_args("sqlite:///./test.db")
    assert "connect_args" in args
    assert args["connect_args"]["check_same_thread"] is False


@pytest.mark.unit
def test_get_engine_args_postgresql() -> None:
    """Verifica argumentos de conexão para PostgreSQL."""
    args = get_engine_args("postgresql://user:pass@localhost:5432/db")
    assert args == {"pool_pre_ping": True}


@pytest.mark.unit
def test_get_db_generator() -> None:
    """Verifica se o generator get_db() instancia e fecha a sessão de banco."""
    gen = get_db()
    session = next(gen)
    assert session is not None
    # Conclui o gerador para disparar o bloco finally com db.close()
    with pytest.raises(StopIteration):
        next(gen)
