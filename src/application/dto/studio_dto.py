"""DTOs para o Studio Unificado de Criação em Lote (Sprint Studio)."""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True, frozen=True)
class StudioNewSourceDTO:
    """Dados de uma nova fonte didática a ser criada no lote."""

    title: str
    content: str
    topic_ids: list[UUID] = field(default_factory=list)
    topic_indices: list[int] = field(default_factory=list)
    content_type: str = "TEXT"


@dataclass(slots=True, frozen=True)
class StudioNewQuestionDTO:
    """Dados de uma nova pergunta aberta a ser criada no lote."""

    prompt: str
    expected_answer: str
    topic_ids: list[UUID] = field(default_factory=list)
    topic_indices: list[int] = field(default_factory=list)
    topic_id: UUID | None = None
    topic_index: int | None = None


@dataclass(slots=True, frozen=True)
class BatchStudioPublishInputDTO:
    """Payload de entrada para publicação atômica em lote no Studio."""

    subject_id: UUID
    new_topics: list[str] = field(default_factory=list)
    new_sources: list[StudioNewSourceDTO] = field(default_factory=list)
    questions: list[StudioNewQuestionDTO] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class BatchStudioPublishResultDTO:
    """Resultado da publicação em lote pelo Studio."""

    subject_id: UUID
    created_topics_count: int
    created_sources_count: int
    created_questions_count: int
    topic_ids: list[UUID] = field(default_factory=list)
    source_ids: list[UUID] = field(default_factory=list)
    question_ids: list[UUID] = field(default_factory=list)
