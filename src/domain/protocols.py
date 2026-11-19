"""Protocolos puros de domínio (Clean Architecture - Camada 1)."""

from typing import Any, Protocol


class IRandomGenerator(Protocol):
    """Protocolo abstrato para injeção de geradores de números pseudoaleatórios."""

    def randint(self, a: int, b: int) -> int:
        """Retorna um inteiro aleatório N tal que a <= N <= b."""
        ...

    def shuffle(self, items: list[Any]) -> None:
        """Embaralha a lista in-place."""
        ...
