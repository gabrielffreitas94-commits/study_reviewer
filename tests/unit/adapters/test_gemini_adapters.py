"""Testes unitários dos adaptadores Gemini de IA e Embeddings (Sprint 07)."""

import asyncio
from uuid import uuid4

import pytest

from src.adapters.ai.gemini_adapters import (
    GeminiEmbeddingAdapter,
    GeminiQuestionValidatorAdapter,
)
from src.domain.entities import KnowledgeChunk


@pytest.mark.unit
def test_gemini_embedding_adapter_basic() -> None:
    adapter = GeminiEmbeddingAdapter(dimension=128)
    vec = asyncio.run(adapter.generate_embedding("Texto de teste"))
    assert len(vec) == 128
    assert isinstance(vec[0], float)

    batch = asyncio.run(adapter.generate_embeddings_batch(["Texto 1", "Texto 2"]))
    assert len(batch) == 2
    assert len(batch[0]) == 128


@pytest.mark.unit
def test_gemini_embedding_adapter_zero_dimension() -> None:
    adapter = GeminiEmbeddingAdapter(dimension=0)
    vec = asyncio.run(adapter.generate_embedding("Texto"))
    assert vec == []


@pytest.mark.unit
def test_gemini_question_validator_no_chunks() -> None:
    validator = GeminiQuestionValidatorAdapter()
    res = asyncio.run(
        validator.validate_question_grounding(
            prompt="Pergunta?",
            expected_answer="Resposta.",
            context_chunks=[],
        )
    )
    assert res.is_grounded is False
    assert res.confidence_score == 0.0
    assert "Nenhum material de conhecimento" in res.reasoning


@pytest.mark.unit
def test_gemini_question_validator_unsupported_answer() -> None:
    validator = GeminiQuestionValidatorAdapter()
    chunk = KnowledgeChunk(
        source_id=uuid4(),
        topic_id=uuid4(),
        chunk_index=0,
        content="Texto exclusivamente sobre biologia molecular e genética avançada.",
        embedding=(0.1, 0.2),
    )
    res = asyncio.run(
        validator.validate_question_grounding(
            prompt="Como funciona o habeas corpus?",
            expected_answer="Remédio constitucional para locomoção e liberdade.",
            context_chunks=[chunk],
        )
    )
    assert res.is_grounded is False
    assert res.confidence_score <= 0.50
    assert "não corroboram" in res.reasoning
