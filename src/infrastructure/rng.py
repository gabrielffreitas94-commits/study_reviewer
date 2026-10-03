"""Implementação concreta do gerador de aleatoriedade usando a biblioteca padrão (Camada 4)."""

import random
from typing import Any

from src.domain.protocols import IRandomGenerator


class SystemRandomGenerator(IRandomGenerator):
    """Implementa o protocolo IRandomGenerator utilizando o gerador criptográfico do sistema."""

    def __init__(self) -> None:
        self._rng = random.SystemRandom()

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def shuffle(self, items: list[Any]) -> None:
        self._rng.shuffle(items)


default_rng = SystemRandomGenerator()
