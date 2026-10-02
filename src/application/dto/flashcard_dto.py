"""DTOs para Flashcards (Clean Architecture - Camada 2)."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class CreateFlashcardDTO:
    """Dados de entrada para criação de Flashcard."""

    topic_id: UUID
    front: str
    back: str


@dataclass(frozen=True)
class FlashcardDTO:
    """Dados de saída representando um Flashcard."""

    id: UUID
    topic_id: UUID
    front: str
    back: str
    position: int
    created_at: date
