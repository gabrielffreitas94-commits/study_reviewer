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


class IEmbeddingService(Protocol):
    """Protocolo abstrato para vetorização semântica (Embedding)."""

    async def generate_embedding(self, text: str) -> list[float]:
        """Gera o vetor denso de embedding para o texto fornecido."""
        ...

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Gera vetores densos em lote para múltiplos fragmentos de texto."""
        ...


class IKnowledgeValidationService(Protocol):
    """Protocolo abstrato para auditoria de fidelidade factual de questões via RAG."""

    async def validate_question_grounding(
        self,
        prompt: str,
        expected_answer: str,
        context_chunks: list[Any],
    ) -> Any:
        """Avalia se o prompt e o gabarito possuem respaldo nos chunks fornecidos."""
        ...
