"""DTOs para gerenciamento da base de conhecimento e validação RAG (Sprint 07)."""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CreateKnowledgeSourceRequest:
    """Dados de requisição para ingestão de material didático."""

    title: str
    content: str
    content_type: str = "TEXT"


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


@dataclass(slots=True, frozen=True)
class KnowledgeChunkResponse:
    """Representação serializável de um fragmento semântico de conhecimento."""

    id: UUID
    source_id: UUID
    topic_id: UUID
    chunk_index: int
    content: str
    token_estimate: int


@dataclass(slots=True, frozen=True)
class ValidateQuestionWithKnowledgeRequest:
    """Dados para validação factual de uma questão contra a base do tema."""

    prompt: str
    expected_answer: str
    question_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class ValidationResultResponse:
    """Resultado da auditoria de validação factual via RAG."""

    is_grounded: bool
    confidence_score: float
    evidence_chunk_ids: list[str] = field(default_factory=list)
    evidence_quotes: list[str] = field(default_factory=list)
    reasoning: str = ""
    suggested_improvements: list[str] = field(default_factory=list)
