"""DTOs para Estudo e Navegação da Pool (Clean Architecture - Camada 2)."""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class GetNextCardDTO:
    """Filtros para obtenção do próximo card."""

    subject_id: UUID | None = None
    topic_id: UUID | None = None


@dataclass(frozen=True)
class StudyCardDTO:
    """Card formatado para estudo ativo (ADR-004)."""

    id: UUID
    front: str
    back: str
    position: int
    current_index: int
    total_cards: int
    round_number: int
    round_shuffled: bool
    topic_ids: list[UUID] = field(default_factory=list)
    topic_names: list[str] = field(default_factory=list)
    topic_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.topic_id is not None and not self.topic_ids:
            object.__setattr__(self, "topic_ids", [self.topic_id])
        elif self.topic_ids and self.topic_id is None:
            object.__setattr__(self, "topic_id", self.topic_ids[0])
