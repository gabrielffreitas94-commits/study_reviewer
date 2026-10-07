"""Serviço de relógio do sistema para injeção de dependência temporal.
Camada 4 - Infraestrutura.
"""

from datetime import UTC, date, datetime

from src.application.ports.repositories import IClockService


class SystemClockService(IClockService):
    """Implementação padrão de relógio utilizando o tempo real do sistema."""

    def today(self) -> date:
        return date.today()

    def now(self) -> datetime:
        return datetime.now(UTC)


system_clock = SystemClockService()
