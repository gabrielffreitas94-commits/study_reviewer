"""DTOs para Flashcards (Clean Architecture - Camada 2)."""

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateFlashcardDTO:
    """Dados de entrada para criação de Flashcard (ADR-004)."""

    front: str
    back: str
    topic_ids: list[UUID] = field(default_factory=list)
    topic_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.topic_id is not None and not self.topic_ids:
            object.__setattr__(self, "topic_ids", [self.topic_id])


@dataclass(frozen=True, slots=True)
class FlashcardDTO:
    """Dados de saída representando um Flashcard (ADR-004)."""

    id: UUID
    front: str
    back: str
    position: int
    created_at: date
    topic_ids: list[UUID] = field(default_factory=list)
    topic_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.topic_id is not None and not self.topic_ids:
            object.__setattr__(self, "topic_ids", [self.topic_id])
        elif self.topic_ids and self.topic_id is None:
            object.__setattr__(self, "topic_id", self.topic_ids[0])
