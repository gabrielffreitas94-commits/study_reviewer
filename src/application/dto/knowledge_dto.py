"""DTOs para gerenciamento de materiais didáticos locais."""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CreateKnowledgeSourceRequest:
    """Dados de requisição para ingestão de material didático."""

    title: str
    content: str
    content_type: str = "TEXT"
    topic_ids: list[UUID] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class LinkKnowledgeSourceRequest:
    """Dados para vincular/desvincular temas de uma fonte de conhecimento existente."""

    source_id: UUID
    topic_ids: list[UUID]


@dataclass(slots=True, frozen=True)
class KnowledgeSourceResponse:
    """Representação serializável de uma fonte de conhecimento."""

    id: UUID
    topic_id: UUID
    title: str
    content_type: str
    total_chunks: int
    char_count: int
    created_at: str
    topic_ids: list[UUID] = field(default_factory=list)
