"""DTOs para Estudo e Navegação da Pool (Clean Architecture - Camada 2)."""

from dataclasses import dataclass, field
from datetime import datetime
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
    session_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.topic_id is not None and not self.topic_ids:
            object.__setattr__(self, "topic_ids", [self.topic_id])
        elif self.topic_ids and self.topic_id is None:
            object.__setattr__(self, "topic_id", self.topic_ids[0])


@dataclass(frozen=True)
class StudyBatchDTO:
    """Lote paginado de flashcards para estudo (ex: 100 cards por requisição)."""

    cards: list[StudyCardDTO]
    total_cards: int
    round_number: int
    has_more: bool


@dataclass(frozen=True)
class StudyEventDTO:
    """Evento individual de revisão de card registrado pelo estudante (PRD v7.0)."""

    card_id: UUID
    reviewed_at: datetime
    status: str
    id: UUID | None = None
    session_id: UUID | None = None
    device_id: str | None = None


@dataclass(frozen=True)
class SyncStudyBatchDTO:
    """Lote de eventos para sincronização de progresso e convergência de cursor."""

    session_id: UUID
    events: list[StudyEventDTO]
    batch_index: int | None = None


@dataclass(frozen=True)
class SyncStudyResultDTO:
    """Resultado da ingestão em lote de eventos de estudo."""

    synced_count: int
    session_id: UUID
    current_index: int
    status: str = "ok"
