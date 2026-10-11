"""Testes unitários das entidades de domínio de conhecimento (Sprint 07)."""

from datetime import date
from uuid import uuid4

import pytest

from src.domain.entities import KnowledgeChunk, KnowledgeSource, ValidationResult
from src.domain.exceptions import (
    DomainValidationError,
    EmptyKnowledgeContentError,
    InvalidEmbeddingError,
)


@pytest.mark.unit
def test_create_valid_knowledge_source() -> None:
    topic_id = uuid4()
    source = KnowledgeSource(
        topic_id=topic_id,
        title="Manual de Direito Constitucional",
        content_type="BOOK_CHAPTER",
        total_chunks=12,
        char_count=18500,
    )
    assert source.title == "Manual de Direito Constitucional"
    assert source.topic_id == topic_id
    assert source.content_type == "BOOK_CHAPTER"
    assert source.total_chunks == 12
    assert source.char_count == 18500
    assert source.created_at == date.today()


@pytest.mark.unit
def test_knowledge_source_title_validation() -> None:
    topic_id = uuid4()
    with pytest.raises(DomainValidationError, match="entre 2 e 200 caracteres"):
        KnowledgeSource(topic_id=topic_id, title="A")

    with pytest.raises(DomainValidationError, match="entre 2 e 200 caracteres"):
        KnowledgeSource(topic_id=topic_id, title="x" * 201)


@pytest.mark.unit
def test_knowledge_source_numeric_invariants() -> None:
    topic_id = uuid4()
    with pytest.raises(DomainValidationError, match="total_chunks não pode ser negativo"):
        KnowledgeSource(topic_id=topic_id, title="Válido", total_chunks=-1)

    with pytest.raises(DomainValidationError, match="char_count não pode ser negativo"):
        KnowledgeSource(topic_id=topic_id, title="Válido", char_count=-5)


@pytest.mark.unit
def test_create_valid_knowledge_chunk() -> None:
    source_id = uuid4()
    topic_id = uuid4()
    embedding = (0.1, 0.2, 0.3)
    chunk = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=0,
        content="Conteúdo relevante sobre direitos fundamentais.",
        embedding=embedding,
        token_estimate=8,
    )
    assert chunk.source_id == source_id
    assert chunk.topic_id == topic_id
    assert chunk.chunk_index == 0
    assert chunk.content == "Conteúdo relevante sobre direitos fundamentais."
    assert chunk.embedding == embedding
    assert chunk.token_estimate == 8


@pytest.mark.unit
def test_knowledge_chunk_validations() -> None:
    source_id = uuid4()
    topic_id = uuid4()

    with pytest.raises(EmptyKnowledgeContentError, match="Conteúdo do chunk não pode ser vazio"):
        KnowledgeChunk(
            source_id=source_id,
            topic_id=topic_id,
            chunk_index=0,
            content="   ",
            embedding=(0.1, 0.2),
        )

    with pytest.raises(DomainValidationError, match="Índice do chunk não pode ser negativo"):
        KnowledgeChunk(
            source_id=source_id,
            topic_id=topic_id,
            chunk_index=-1,
            content="Texto válido",
            embedding=(0.1, 0.2),
        )

    with pytest.raises(InvalidEmbeddingError, match="Vetor de embedding não pode ser vazio"):
        KnowledgeChunk(
            source_id=source_id,
            topic_id=topic_id,
            chunk_index=0,
            content="Texto válido",
            embedding=(),
        )


@pytest.mark.unit
def test_validation_result_entity() -> None:
    chunk_id = uuid4()
    res = ValidationResult(
        is_grounded=True,
        confidence_score=0.95,
        evidence_chunk_ids=(chunk_id,),
        evidence_quotes=("Art. 5º da CF/88",),
        reasoning="A afirmação condiz com o texto constitucional.",
        suggested_improvements=(),
    )
    assert res.is_grounded is True
    assert res.confidence_score == 0.95
    assert len(res.evidence_chunk_ids) == 1
    assert res.evidence_quotes[0] == "Art. 5º da CF/88"


@pytest.mark.unit
def test_validation_result_invariants() -> None:
    with pytest.raises(DomainValidationError, match="confidence_score deve estar entre 0.0 e 1.0"):
        ValidationResult(
            is_grounded=True,
            confidence_score=1.5,
            evidence_chunk_ids=(),
            evidence_quotes=(),
            reasoning="Inválido",
            suggested_improvements=(),
        )

    with pytest.raises(DomainValidationError, match="confidence_score deve estar entre 0.0 e 1.0"):
        ValidationResult(
            is_grounded=False,
            confidence_score=-0.1,
            evidence_chunk_ids=(),
            evidence_quotes=(),
            reasoning="Inválido",
            suggested_improvements=(),
        )
