"""Testes unitários para o serviço de relógio de infraestrutura."""

from datetime import UTC, date, datetime

import pytest

from src.infrastructure.clock import SystemClockService, system_clock


@pytest.mark.unit
def test_system_clock_service() -> None:
    clock = SystemClockService()
    assert clock.today() == date.today()
    now = clock.now()
    assert isinstance(now, datetime)
    assert now.tzinfo == UTC
    assert system_clock.today() == date.today()
