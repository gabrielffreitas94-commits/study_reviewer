"""Testes unitários dos casos de uso de conhecimento e RAG (Sprint 07)."""

import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from src.application.dto.knowledge_dto import (
    CreateKnowledgeSourceRequest,
    ValidateQuestionWithKnowledgeRequest,
)
from src.application.use_cases.knowledge_use_cases import (
    DeleteKnowledgeSourceUseCase,
    GetTopicKnowledgeSourcesUseCase,
    IngestKnowledgeSourceUseCase,
    ValidateQuestionWithKnowledgeUseCase,
)
from src.domain.entities import KnowledgeChunk, KnowledgeSource, Subject, Topic, ValidationResult
from src.domain.exceptions import (
    EmptyKnowledgeContentError,
    EntityNotFoundError,
    ResourceOwnershipError,
)


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def subject(user_id: UUID) -> Subject:
    return Subject(name="Direito Constitucional", owner_id=user_id, is_public=False)


@pytest.fixture
def topic(subject: Subject) -> Topic:
    return Topic(subject_id=subject.id, name="Controle de Constitucionalidade")


@pytest.mark.unit
def test_ingest_knowledge_source_success(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    source_repo = Mock()
    chunk_repo = Mock()
    topic_repo = Mock()
    subject_repo = Mock()
    embedding_service = AsyncMock()

    topic_repo.get_by_id.return_value = topic
    subject_repo.get_by_id.return_value = subject
    embedding_service.generate_embeddings_batch.side_effect = lambda texts: [
        [0.1, 0.2, 0.3] for _ in texts
    ]
    source_repo.save.side_effect = lambda s: s

    use_case = IngestKnowledgeSourceUseCase(
        source_repo=source_repo,
        chunk_repo=chunk_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
        embedding_service=embedding_service,
    )

    req = CreateKnowledgeSourceRequest(
        title="Capítulo 1 - Teoria da Constituição",
        content=("A Constituição é a lei fundamental e suprema de um Estado soberano. " * 15),
        content_type="BOOK_CHAPTER",
    )

    res = asyncio.run(use_case.execute(user_id=user_id, topic_id=topic.id, request=req))

    assert res.title == "Capítulo 1 - Teoria da Constituição"
    assert res.topic_id == topic.id
    assert res.total_chunks >= 1
    assert res.char_count > 0

    source_repo.save.assert_called_once()
    chunk_repo.save_batch.assert_called_once()


@pytest.mark.unit
def test_ingest_knowledge_source_ownership_error(
    other_user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    source_repo = Mock()
    chunk_repo = Mock()
    topic_repo = Mock(get_by_id=Mock(return_value=topic))
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    embedding_service = AsyncMock()

    use_case = IngestKnowledgeSourceUseCase(
        source_repo=source_repo,
        chunk_repo=chunk_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
        embedding_service=embedding_service,
    )

    req = CreateKnowledgeSourceRequest(
        title="Tentativa IDOR",
        content="Texto suficiente para passar no tamanho mínimo de vinte caracteres.",
    )

    with pytest.raises(ResourceOwnershipError, match="Apenas o proprietário"):
        asyncio.run(use_case.execute(user_id=other_user_id, topic_id=topic.id, request=req))


@pytest.mark.unit
def test_ingest_knowledge_source_content_too_short(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    topic_repo = Mock(get_by_id=Mock(return_value=topic))
    subject_repo = Mock(get_by_id=Mock(return_value=subject))

    use_case = IngestKnowledgeSourceUseCase(
        source_repo=Mock(),
        chunk_repo=Mock(),
        topic_repo=topic_repo,
        subject_repo=subject_repo,
        embedding_service=AsyncMock(),
    )

    req = CreateKnowledgeSourceRequest(title="Muito Curto", content="Texto < 20")

    with pytest.raises(EmptyKnowledgeContentError, match="pelo menos 20 caracteres úteis"):
        asyncio.run(use_case.execute(user_id=user_id, topic_id=topic.id, request=req))


@pytest.mark.unit
def test_get_topic_knowledge_sources(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    source_repo = Mock()
    topic_repo = Mock(get_by_id=Mock(return_value=topic))
    subject_repo = Mock(get_by_id=Mock(return_value=subject))

    s1 = KnowledgeSource(
        topic_id=topic.id,
        title="Manual Constitucional",
        total_chunks=5,
        char_count=5000,
    )
    source_repo.list_by_topic.return_value = [s1]

    use_case = GetTopicKnowledgeSourcesUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    sources = asyncio.run(use_case.execute(user_id=user_id, topic_id=topic.id))
    assert len(sources) == 1
    assert sources[0].title == "Manual Constitucional"


@pytest.mark.unit
def test_delete_knowledge_source(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    source_repo = Mock()
    chunk_repo = Mock()
    topic_repo = Mock(get_by_id=Mock(return_value=topic))
    subject_repo = Mock(get_by_id=Mock(return_value=subject))

    s1 = KnowledgeSource(topic_id=topic.id, title="Para Deletar")
    source_repo.get_by_id.return_value = s1

    use_case = DeleteKnowledgeSourceUseCase(
        source_repo=source_repo,
        chunk_repo=chunk_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    asyncio.run(use_case.execute(user_id=user_id, source_id=s1.id))

    chunk_repo.delete_by_source.assert_called_once_with(s1.id)
    source_repo.delete.assert_called_once_with(s1.id)


@pytest.mark.unit
def test_validate_question_with_knowledge_success(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    chunk_repo = Mock()
    topic_repo = Mock(get_by_id=Mock(return_value=topic))
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    embedding_service = AsyncMock()
    validation_service = AsyncMock()

    chunk = KnowledgeChunk(
        source_id=uuid4(),
        topic_id=topic.id,
        chunk_index=0,
        content="O recurso extraordinário é cabível ao STF contra decisão que contrariar a CF.",
        embedding=(0.1, 0.2, 0.3),
    )

    embedding_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
    chunk_repo.search_similar.return_value = [(chunk, 0.95)]

    validation_result = ValidationResult(
        is_grounded=True,
        confidence_score=0.92,
        evidence_chunk_ids=(chunk.id,),
        evidence_quotes=("recurso extraordinário é cabível ao STF",),
        reasoning="Afirmação fundamentada na Constituição.",
        suggested_improvements=(),
    )
    validation_service.validate_question_grounding.return_value = validation_result

    use_case = ValidateQuestionWithKnowledgeUseCase(
        chunk_repo=chunk_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
        embedding_service=embedding_service,
        validation_service=validation_service,
    )

    req = ValidateQuestionWithKnowledgeRequest(
        prompt="Quando cabe recurso extraordinário?",
        expected_answer="Cabe contra decisão de última instância que contrariar a CF.",
    )

    res = asyncio.run(use_case.execute(user_id=user_id, topic_id=topic.id, request=req))

    assert res.is_grounded is True
    assert res.confidence_score == 0.92
    assert str(chunk.id) in res.evidence_chunk_ids


@pytest.mark.unit
def test_validate_question_cold_start_no_chunks(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    chunk_repo = Mock(search_similar=Mock(return_value=[]))
    topic_repo = Mock(get_by_id=Mock(return_value=topic))
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    embedding_service = AsyncMock(generate_embedding=AsyncMock(return_value=[0.1, 0.2]))
    validation_service = AsyncMock()

    use_case = ValidateQuestionWithKnowledgeUseCase(
        chunk_repo=chunk_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
        embedding_service=embedding_service,
        validation_service=validation_service,
    )

    req = ValidateQuestionWithKnowledgeRequest(
        prompt="Qualquer pergunta?",
        expected_answer="Qualquer resposta.",
    )

    res = asyncio.run(use_case.execute(user_id=user_id, topic_id=topic.id, request=req))

    assert res.is_grounded is False
    assert res.confidence_score == 0.0
    assert "Nenhum material de conhecimento" in res.reasoning
    validation_service.validate_question_grounding.assert_not_called()


@pytest.mark.unit
def test_get_topic_knowledge_sources_topic_not_found(user_id: UUID) -> None:
    use_case = GetTopicKnowledgeSourcesUseCase(
        source_repo=Mock(),
        topic_repo=Mock(get_by_id=Mock(return_value=None)),
        subject_repo=Mock(),
    )
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        asyncio.run(use_case.execute(user_id=user_id, topic_id=uuid4()))


@pytest.mark.unit
def test_delete_knowledge_source_topic_not_found(user_id: UUID) -> None:
    source = KnowledgeSource(topic_id=uuid4(), title="Livro")
    use_case = DeleteKnowledgeSourceUseCase(
        source_repo=Mock(get_by_id=Mock(return_value=source)),
        chunk_repo=Mock(),
        topic_repo=Mock(get_by_id=Mock(return_value=None)),
        subject_repo=Mock(),
    )
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        asyncio.run(use_case.execute(user_id=user_id, source_id=source.id))


@pytest.mark.unit
def test_validate_question_topic_not_found(user_id: UUID) -> None:
    use_case = ValidateQuestionWithKnowledgeUseCase(
        chunk_repo=Mock(),
        topic_repo=Mock(get_by_id=Mock(return_value=None)),
        subject_repo=Mock(),
        embedding_service=AsyncMock(),
        validation_service=AsyncMock(),
    )
    req = ValidateQuestionWithKnowledgeRequest(prompt="P", expected_answer="R")
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        asyncio.run(use_case.execute(user_id=user_id, topic_id=uuid4(), request=req))


@pytest.mark.unit
def test_validate_question_permission_denied(
    other_user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    use_case = ValidateQuestionWithKnowledgeUseCase(
        chunk_repo=Mock(),
        topic_repo=Mock(get_by_id=Mock(return_value=topic)),
        subject_repo=Mock(get_by_id=Mock(return_value=subject)),
        embedding_service=AsyncMock(),
        validation_service=AsyncMock(),
    )
    req = ValidateQuestionWithKnowledgeRequest(prompt="P", expected_answer="R")
    with pytest.raises(ResourceOwnershipError, match="Sem permissão para consultar o tema"):
        asyncio.run(use_case.execute(user_id=other_user_id, topic_id=topic.id, request=req))
