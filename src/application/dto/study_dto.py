"""DTOs para Estudo e Navegação da Pool (Clean Architecture - Camada 2)."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetNextCardDTO:
    """Filtros para obtenção do próximo card."""

    subject_id: UUID | None = None
    topic_id: UUID | None = None


@dataclass(frozen=True)
class StudyCardDTO:
    """Card formatado para estudo ativo."""

    id: UUID
    topic_id: UUID
    front: str
    back: str
    position: int
    current_index: int
    total_cards: int
    round_number: int
    round_shuffled: bool
