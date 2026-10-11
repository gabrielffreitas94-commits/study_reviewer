"""Módulo de configuração e captura de telemetria e logs (Camada 4 - Frameworks & Drivers)."""

import collections
import datetime
import logging
from typing import Any


class InMemoryLogHandler(logging.Handler):
    """Handler de logging em memória baseado em anel rotativo (ring buffer)."""

    def __init__(self, maxlen: int = 300) -> None:
        super().__init__()
        self.buffer: collections.deque[dict[str, Any]] = collections.deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        """Captura o registro de log e insere no buffer rotativo."""
        try:
            msg = self.format(record)
            created_dt = datetime.datetime.fromtimestamp(record.created, tz=datetime.UTC)
            formatted_time = created_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            self.buffer.append(
                {
                    "timestamp": record.created,
                    "datetime": formatted_time,
                    "level": record.levelname,
                    "logger": record.name,
                    "message": msg,
                }
            )
        except Exception:  # pragma: no cover
            self.handleError(record)

    def get_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retorna os últimos logs capturados."""
        if limit <= 0:
            return []
        items = list(self.buffer)
        return items[-limit:]

    def clear(self) -> None:
        """Limpa o buffer em memória (útil para testes unitários)."""
        self.buffer.clear()


in_memory_log_handler = InMemoryLogHandler(maxlen=300)
_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
in_memory_log_handler.setFormatter(_formatter)

_root_logger = logging.getLogger()
if in_memory_log_handler not in _root_logger.handlers:
    _root_logger.addHandler(in_memory_log_handler)
    _root_logger.setLevel(logging.INFO)
