"""Testes unitários para o handler de logging em memória e observabilidade."""

import logging

import pytest

from src.infrastructure.logging import InMemoryLogHandler, in_memory_log_handler


@pytest.mark.unit
def test_in_memory_log_handler_emit_and_retrieve() -> None:
    handler = InMemoryLogHandler(maxlen=5)
    handler.setFormatter(logging.Formatter("%(message)s"))

    test_logger = logging.getLogger("test_logger_telemetry")
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.INFO)

    test_logger.info("Primeira mensagem de teste")
    test_logger.warning("Segunda mensagem de aviso")

    logs = handler.get_logs(limit=10)
    assert len(logs) == 2
    assert logs[0]["message"] == "Primeira mensagem de teste"
    assert logs[0]["level"] == "INFO"
    assert logs[1]["message"] == "Segunda mensagem de aviso"
    assert logs[1]["level"] == "WARNING"

    # Test limit <= 0
    assert handler.get_logs(limit=0) == []
    assert handler.get_logs(limit=-1) == []

    # Test buffer maxlen overflow
    for i in range(10):
        test_logger.info(f"Mensagem {i}")

    logs_after = handler.get_logs(limit=10)
    assert len(logs_after) == 5
    assert logs_after[-1]["message"] == "Mensagem 9"

    # Test clear
    handler.clear()
    assert len(handler.get_logs(limit=10)) == 0


@pytest.mark.unit
def test_global_in_memory_log_handler_registered() -> None:
    assert in_memory_log_handler is not None
    root_logger = logging.getLogger()
    assert in_memory_log_handler in root_logger.handlers
