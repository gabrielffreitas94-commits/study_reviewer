"""Testes unitários dos serviços de domínio de RAG e Chunker (Sprint 07)."""

from uuid import uuid4

import pytest

from src.domain.entities import KnowledgeChunk
from src.domain.exceptions import EmptyKnowledgeContentError
from src.domain.services import KnowledgeGroundingService, SemanticChunkerService


@pytest.mark.unit
def test_semantic_chunker_basic_split() -> None:
    text = (
        "O habeas corpus é remédio constitucional. "
        "Ele protege a liberdade de locomoção contra ilegalidade ou abuso de poder. "
        "Já o mandado de segurança protege direito líquido e certo não amparado por habeas corpus. "
        "Ambos são instrumentos de garantia fundamental do cidadão."
    )
    chunks = SemanticChunkerService.chunk_text(text, chunk_size_chars=120, overlap_chars=20)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk.strip()) > 0
        assert len(chunk) <= 150  # tolerância de fronteira de frase


@pytest.mark.unit
def test_semantic_chunker_single_small_chunk() -> None:
    text = "Texto curto que cabe em um único chunk."
    chunks = SemanticChunkerService.chunk_text(text, chunk_size_chars=500, overlap_chars=50)
    assert len(chunks) == 1
    assert chunks[0] == text


@pytest.mark.unit
def test_semantic_chunker_empty_text_error() -> None:
    with pytest.raises(EmptyKnowledgeContentError, match="Texto para chunking não pode ser vazio"):
        SemanticChunkerService.chunk_text("   \n\t  ")


@pytest.mark.unit
def test_semantic_chunker_preserves_sentences_and_normalizes_whitespace() -> None:
    messy_text = "Primeira frase.   \n\n  Segunda frase com quebra   irregular.\nTerceira frase."
    chunks = SemanticChunkerService.chunk_text(messy_text, chunk_size_chars=200, overlap_chars=20)
    assert len(chunks) >= 1
    assert "  " not in chunks[0]  # espaços duplos normalizados


@pytest.mark.unit
def test_knowledge_grounding_cosine_similarity() -> None:
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]
    vec_d = [-1.0, 0.0, 0.0]

    assert pytest.approx(KnowledgeGroundingService.cosine_similarity(vec_a, vec_b), 0.001) == 1.0
    assert pytest.approx(KnowledgeGroundingService.cosine_similarity(vec_a, vec_c), 0.001) == 0.0
    assert pytest.approx(KnowledgeGroundingService.cosine_similarity(vec_a, vec_d), 0.001) == -1.0


@pytest.mark.unit
def test_knowledge_grounding_cosine_similarity_zero_norm() -> None:
    vec_zero = [0.0, 0.0, 0.0]
    vec_a = [1.0, 2.0, 3.0]
    assert KnowledgeGroundingService.cosine_similarity(vec_zero, vec_a) == 0.0


@pytest.mark.unit
def test_knowledge_grounding_rank_chunks() -> None:
    source_id = uuid4()
    topic_id = uuid4()

    c1 = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=0,
        content="Chunk sobre direito penal",
        embedding=(1.0, 0.0, 0.0),
    )
    c2 = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=1,
        content="Chunk sobre direito civil",
        embedding=(0.5, 0.5, 0.0),
    )
    c3 = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=2,
        content="Chunk sobre culinária",
        embedding=(0.0, 1.0, 0.0),
    )

    query_vec = [1.0, 0.0, 0.0]
    ranked = KnowledgeGroundingService.rank_chunks_by_similarity(query_vec, [c1, c2, c3], top_k=2)

    assert len(ranked) == 2
    assert ranked[0][0].id == c1.id
    assert pytest.approx(ranked[0][1], 0.01) == 1.0
    assert ranked[1][0].id == c2.id


@pytest.mark.unit
def test_semantic_chunker_with_overlap_sentences() -> None:
    text = (
        "Frase 1 curta. Frase 2 média tamanho. "
        "Frase 3 longa com mais texto relevante. Frase 4 final."
    )
    chunks = SemanticChunkerService.chunk_text(text, chunk_size_chars=40, overlap_chars=25)
    assert len(chunks) >= 2


@pytest.mark.unit
def test_knowledge_grounding_cosine_similarity_different_lengths() -> None:
    assert KnowledgeGroundingService.cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert KnowledgeGroundingService.cosine_similarity([], []) == 0.0
