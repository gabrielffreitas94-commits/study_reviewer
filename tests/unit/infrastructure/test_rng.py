"""Testes unitários para o gerador de aleatoriedade do sistema."""

import pytest

from src.infrastructure.rng import default_rng


@pytest.mark.unit
def test_system_random_generator_shuffle() -> None:
    """Verifica que o método shuffle embaralha a lista in-place."""
    items = [1, 2, 3, 4, 5]
    default_rng.shuffle(items)
    assert len(items) == 5
    assert set(items) == {1, 2, 3, 4, 5}
