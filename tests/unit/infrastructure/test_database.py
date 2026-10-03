"""Testes unitários para a configuração de banco de dados (Camada 4 - Infraestrutura)."""

from unittest.mock import MagicMock

import pytest

from src.infrastructure.database import _setup_sqlite_functions, get_db, get_engine_args


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


@pytest.mark.unit
def test_setup_sqlite_functions_with_sqlite_connection() -> None:
    """Verifica registro da função lower quando a conexão suporta create_function."""
    conn = MagicMock()
    _setup_sqlite_functions(conn, None)
    conn.create_function.assert_called_once_with("lower", 1, str.lower)


@pytest.mark.unit
def test_setup_sqlite_functions_without_create_function() -> None:
    """Verifica comportamento gracioso quando a conexão não possui create_function (PostgreSQL)."""
    conn = object()
    _setup_sqlite_functions(conn, None)
