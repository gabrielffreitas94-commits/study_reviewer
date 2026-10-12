"""Testes unitários do caso de uso de publicação em lote no Studio (BatchStudioPublishUseCase)."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from src.application.dto.knowledge_dto import KnowledgeSourceResponse
from src.application.dto.studio_dto import (
    BatchStudioPublishInputDTO,
    StudioNewQuestionDTO,
    StudioNewSourceDTO,
)
from src.application.use_cases.studio_use_cases import BatchStudioPublishUseCase
from src.domain.entities import Subject, Topic
from src.domain.exceptions import (
    DomainValidationError,
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
    return Subject(name="Direito Administrativo", owner_id=user_id, is_public=False)


@pytest.fixture
def existing_topic(subject: Subject) -> Topic:
    return Topic(subject_id=subject.id, name="Atos Administrativos")


@pytest.fixture
def clock_mock() -> Mock:
    clock = Mock()
    clock.today.return_value = date(2026, 10, 12)
    return clock


@pytest.mark.unit
def test_batch_studio_publish_success(
    user_id: UUID,
    subject: Subject,
    existing_topic: Topic,
    clock_mock: Mock,
) -> None:
    subject_repo = Mock()
    subject_repo.get_by_id.return_value = subject

    topic_repo = Mock()
    topic_repo.list_by_subject.return_value = [existing_topic]
    topic_repo.save.side_effect = lambda t: t

    question_repo = Mock()
    question_repo.save.side_effect = lambda q: q

    progress_repo = Mock()
    progress_repo.save.side_effect = lambda p: p

    ingest_use_case = AsyncMock()
    mock_src_id = uuid4()
    ingest_use_case.execute.return_value = KnowledgeSourceResponse(
        id=mock_src_id,
        topic_id=existing_topic.id,
        topic_ids=(existing_topic.id,),
        title="Doutrina Maria Sylvia",
        content_type="TEXT",
        total_chunks=3,
        char_count=1500,
        created_at=date(2026, 10, 12),
    )

    uow = Mock()

    use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=topic_repo,
        question_repo=question_repo,
        progress_repo=progress_repo,
        ingest_knowledge_use_case=ingest_use_case,
        clock=clock_mock,
        uow=uow,
    )

    dto = BatchStudioPublishInputDTO(
        subject_id=subject.id,
        new_topics=["Poderes Administrativos", "Licitações"],
        new_sources=[
            StudioNewSourceDTO(
                title="Doutrina Maria Sylvia",
                content="Conteúdo completo sobre poderes administrativos e licitações na lei 14.133.",
                topic_indices=[0, 1],
                topic_ids=[existing_topic.id],
                content_type="TEXT",
            )
        ],
        questions=[
            StudioNewQuestionDTO(
                prompt="Quais são os requisitos do ato administrativo?",
                expected_answer="Competência, finalidade, forma, motivo e objeto.",
                topic_id=existing_topic.id,
            ),
            StudioNewQuestionDTO(
                prompt="O que é poder de polícia discricionário?",
                expected_answer="É a faculdade da administração valorar a oportunidade e conveniência.",
                topic_index=0,
            ),
        ],
    )

    result = asyncio.run(use_case.execute(user_id=user_id, dto=dto))

    assert result.subject_id == subject.id
    assert result.created_topics_count == 2
    assert result.created_sources_count == 1
    assert result.created_questions_count == 2
    assert len(result.topic_ids) == 2
    assert len(result.source_ids) == 1
    assert len(result.question_ids) == 2

    assert topic_repo.save.call_count == 2
    assert ingest_use_case.execute.call_count == 1
    assert question_repo.save.call_count == 2
    assert progress_repo.save.call_count == 2
    uow.commit.assert_called_once()


@pytest.mark.unit
def test_batch_studio_publish_subject_not_found(user_id: UUID, clock_mock: Mock) -> None:
    subject_repo = Mock(get_by_id=Mock(return_value=None))
    use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=Mock(),
        question_repo=Mock(),
        progress_repo=Mock(),
        ingest_knowledge_use_case=AsyncMock(),
        clock=clock_mock,
    )
    dto = BatchStudioPublishInputDTO(
        subject_id=uuid4(),
        new_topics=[],
        new_sources=[],
        questions=[StudioNewQuestionDTO(prompt="P", expected_answer="R")],
    )
    with pytest.raises(EntityNotFoundError, match="Matéria não encontrada"):
        asyncio.run(use_case.execute(user_id=user_id, dto=dto))


@pytest.mark.unit
def test_batch_studio_publish_ownership_error(
    other_user_id: UUID,
    subject: Subject,
    clock_mock: Mock,
) -> None:
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=Mock(),
        question_repo=Mock(),
        progress_repo=Mock(),
        ingest_knowledge_use_case=AsyncMock(),
        clock=clock_mock,
    )
    dto = BatchStudioPublishInputDTO(
        subject_id=subject.id,
        new_topics=[],
        new_sources=[],
        questions=[StudioNewQuestionDTO(prompt="P", expected_answer="R")],
    )
    with pytest.raises(ResourceOwnershipError, match="proprietário da matéria"):
        asyncio.run(use_case.execute(user_id=other_user_id, dto=dto))


@pytest.mark.unit
def test_batch_studio_publish_empty_questions_error(
    user_id: UUID,
    subject: Subject,
    clock_mock: Mock,
) -> None:
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    topic_repo = Mock(list_by_subject=Mock(return_value=[]))
    use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=topic_repo,
        question_repo=Mock(),
        progress_repo=Mock(),
        ingest_knowledge_use_case=AsyncMock(),
        clock=clock_mock,
    )
    dto = BatchStudioPublishInputDTO(
        subject_id=subject.id,
        new_topics=["Tema 1"],
        new_sources=[],
        questions=[],
    )
    with pytest.raises(DomainValidationError, match="pelo menos uma pergunta"):
        asyncio.run(use_case.execute(user_id=user_id, dto=dto))


@pytest.mark.unit
def test_batch_studio_publish_no_topics_available_error(
    user_id: UUID,
    subject: Subject,
    clock_mock: Mock,
) -> None:
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    topic_repo = Mock(list_by_subject=Mock(return_value=[]))
    use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=topic_repo,
        question_repo=Mock(),
        progress_repo=Mock(),
        ingest_knowledge_use_case=AsyncMock(),
        clock=clock_mock,
    )
    dto = BatchStudioPublishInputDTO(
        subject_id=subject.id,
        new_topics=[],
        new_sources=[],
        questions=[StudioNewQuestionDTO(prompt="P", expected_answer="R")],
    )
    with pytest.raises(DomainValidationError, match="não possui temas"):
        asyncio.run(use_case.execute(user_id=user_id, dto=dto))


@pytest.mark.unit
def test_batch_studio_publish_empty_prompt_or_answer_error(
    user_id: UUID,
    subject: Subject,
    existing_topic: Topic,
    clock_mock: Mock,
) -> None:
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    topic_repo = Mock(list_by_subject=Mock(return_value=[existing_topic]))
    use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=topic_repo,
        question_repo=Mock(),
        progress_repo=Mock(),
        ingest_knowledge_use_case=AsyncMock(),
        clock=clock_mock,
    )
    dto = BatchStudioPublishInputDTO(
        subject_id=subject.id,
        new_topics=[],
        new_sources=[],
        questions=[StudioNewQuestionDTO(prompt="   ", expected_answer="R")],
    )
    with pytest.raises(DomainValidationError, match="não podem ser vazios"):
        asyncio.run(use_case.execute(user_id=user_id, dto=dto))


@pytest.mark.unit
def test_batch_studio_publish_rollback_on_error(
    user_id: UUID,
    subject: Subject,
    existing_topic: Topic,
    clock_mock: Mock,
) -> None:
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    topic_repo = Mock(list_by_subject=Mock(return_value=[existing_topic]))
    question_repo = Mock()
    question_repo.save.side_effect = RuntimeError("Falha de disco simulada")
    uow = Mock()

    use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=topic_repo,
        question_repo=question_repo,
        progress_repo=Mock(),
        ingest_knowledge_use_case=AsyncMock(),
        clock=clock_mock,
        uow=uow,
    )
    dto = BatchStudioPublishInputDTO(
        subject_id=subject.id,
        new_topics=[],
        new_sources=[],
        questions=[
            StudioNewQuestionDTO(prompt="Pergunta válida", expected_answer="Resposta válida")
        ],
    )
    with pytest.raises(RuntimeError, match="Falha de disco simulada"):
        asyncio.run(use_case.execute(user_id=user_id, dto=dto))

    uow.rollback.assert_called_once()


@pytest.mark.unit
def test_batch_studio_publish_fallback_to_created_topics(
    user_id: UUID,
    subject: Subject,
    clock_mock: Mock,
) -> None:
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    topic_repo = Mock(list_by_subject=Mock(return_value=[]))
    topic_repo.save = Mock()
    question_repo = Mock()
    progress_repo = Mock()
    ingest_use_case = AsyncMock()
    ingest_use_case.execute.return_value = Mock(id=uuid4())

    use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=topic_repo,
        question_repo=question_repo,
        progress_repo=progress_repo,
        ingest_knowledge_use_case=ingest_use_case,
        clock=clock_mock,
    )
    dto = BatchStudioPublishInputDTO(
        subject_id=subject.id,
        new_topics=["Novo Tema A"],
        new_sources=[
            StudioNewSourceDTO(
                title="Material Didático",
                content="Conteúdo longo com mais de vinte caracteres válidos.",
                topic_ids=[],
                topic_indices=[],
            )
        ],
        questions=[StudioNewQuestionDTO(prompt="Pergunta?", expected_answer="Resposta.")],
    )
    res = asyncio.run(use_case.execute(user_id=user_id, dto=dto))
    assert res.created_topics_count == 1
    assert res.created_sources_count == 1
    assert res.created_questions_count == 1


@pytest.mark.unit
def test_batch_studio_publish_fallback_to_existing_topics(
    user_id: UUID,
    subject: Subject,
    existing_topic: Topic,
    clock_mock: Mock,
) -> None:
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    topic_repo = Mock(list_by_subject=Mock(return_value=[existing_topic]))
    question_repo = Mock()
    progress_repo = Mock()
    ingest_use_case = AsyncMock()
    ingest_use_case.execute.return_value = Mock(id=uuid4())

    use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=topic_repo,
        question_repo=question_repo,
        progress_repo=progress_repo,
        ingest_knowledge_use_case=ingest_use_case,
        clock=clock_mock,
    )
    dto = BatchStudioPublishInputDTO(
        subject_id=subject.id,
        new_topics=[],
        new_sources=[
            StudioNewSourceDTO(
                title="Material Didático",
                content="Conteúdo longo com mais de vinte caracteres válidos.",
                topic_ids=[],
                topic_indices=[],
            )
        ],
        questions=[StudioNewQuestionDTO(prompt="Pergunta?", expected_answer="Resposta.")],
    )
    res = asyncio.run(use_case.execute(user_id=user_id, dto=dto))
    assert res.created_topics_count == 0
    assert res.created_sources_count == 1
    assert res.created_questions_count == 1
