"""Testes unitários da entidade de domínio KnowledgeSource."""

from datetime import date
from uuid import uuid4

import pytest

from src.domain.entities import KnowledgeSource
from src.domain.exceptions import DomainValidationError


@pytest.mark.unit
def test_create_valid_knowledge_source() -> None:
    """Valida criação nominal de KnowledgeSource com tópico único e valores padrão."""
    topic_id = uuid4()
    source = KnowledgeSource(
        topic_id=topic_id,
        title="  Manual de Direito Constitucional  ",
        content_type="BOOK_CHAPTER",
        total_chunks=12,
        char_count=18500,
        raw_text="  Texto base sobre direitos fundamentais.  ",
    )
    assert source.title == "Manual de Direito Constitucional"
    assert source.topic_id == topic_id
    assert source.topic_ids == (topic_id,)
    assert source.content_type == "BOOK_CHAPTER"
    assert source.total_chunks == 12
    assert source.char_count == 18500
    assert source.raw_text == "Texto base sobre direitos fundamentais."
    assert source.node_id is None
    assert source.created_at == date.today()


@pytest.mark.unit
def test_create_knowledge_source_with_multiple_topics_and_legacy_positional() -> None:
    """Valida associação N:N via topic_ids e compatibilidade com chamada posicional legada."""
    t1, t2 = uuid4(), uuid4()
    multi = KnowledgeSource(title="Material Multi", topic_ids=[t1, t2])
    assert multi.topic_ids == (t1, t2)
    assert multi.topic_id == t1

    legacy = KnowledgeSource(t1, "Título Legado")  # type: ignore[arg-type]
    assert legacy.topic_id == t1
    assert legacy.title == "Título Legado"
    assert legacy.content_type == "TEXT"


@pytest.mark.unit
def test_create_knowledge_source_with_node_id_fallback() -> None:
    """Valida que node_id é usado como fallback para topic_ids quando nenhum tema é passado."""
    node_id = uuid4()
    source = KnowledgeSource(title="Pergaminho do Nó", node_id=node_id)
    assert source.node_id == node_id
    assert source.topic_ids == (node_id,)
    assert source.topic_id == node_id


@pytest.mark.unit
def test_knowledge_source_title_validation() -> None:
    """Rejeita títulos menores que 2 ou maiores que 200 caracteres."""
    topic_id = uuid4()
    with pytest.raises(DomainValidationError, match="entre 2 e 200 caracteres"):
        KnowledgeSource(topic_id=topic_id, title="A")

    with pytest.raises(DomainValidationError, match="entre 2 e 200 caracteres"):
        KnowledgeSource(topic_id=topic_id, title="  A  ")

    with pytest.raises(DomainValidationError, match="entre 2 e 200 caracteres"):
        KnowledgeSource(topic_id=topic_id, title="x" * 201)


@pytest.mark.unit
def test_knowledge_source_topics_validation() -> None:
    """Rejeita ausência de temas ou temas duplicados em topic_ids."""
    with pytest.raises(DomainValidationError, match="pelo menos 1 tema"):
        KnowledgeSource(title="Sem Temas", topic_ids=())

    dup_id = uuid4()
    with pytest.raises(DomainValidationError, match="temas duplicados"):
        KnowledgeSource(title="Temas Duplicados", topic_ids=(dup_id, dup_id))


@pytest.mark.unit
def test_knowledge_source_numeric_invariants() -> None:
    """Rejeita valores negativos para total_chunks e char_count."""
    topic_id = uuid4()
    with pytest.raises(DomainValidationError, match="total_chunks não pode ser negativo"):
        KnowledgeSource(topic_id=topic_id, title="Válido", total_chunks=-1)

    with pytest.raises(DomainValidationError, match="char_count não pode ser negativo"):
        KnowledgeSource(topic_id=topic_id, title="Válido", char_count=-5)
