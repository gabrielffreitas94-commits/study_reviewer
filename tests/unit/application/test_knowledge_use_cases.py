"""Testes unitários dos casos de uso de gestão de materiais didáticos locais."""

import asyncio
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from src.application.dto.knowledge_dto import (
    CreateKnowledgeSourceRequest,
    LinkKnowledgeSourceRequest,
)
from src.application.use_cases.knowledge_use_cases import (
    DeleteKnowledgeSourceUseCase,
    GetTopicKnowledgeSourcesUseCase,
    IngestKnowledgeSourceUseCase,
    LinkKnowledgeSourceToTopicsUseCase,
)
from src.domain.entities import KnowledgeSource, Subject, Topic
from src.domain.exceptions import (
    DomainValidationError,
    EmptyKnowledgeContentError,
    EntityNotFoundError,
    KnowledgeSourceNotFoundError,
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
def public_subject(user_id: UUID) -> Subject:
    return Subject(name="Direito Administrativo Público", owner_id=user_id, is_public=True)


@pytest.fixture
def topic(subject: Subject) -> Topic:
    return Topic(subject_id=subject.id, name="Controle de Constitucionalidade")


@pytest.mark.unit
def test_ingest_knowledge_source_success_with_topic_id(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    """Valida ingestão local de material didático usando topic_id fallback."""
    source_repo = Mock()
    topic_repo = Mock(get_by_id=Mock(return_value=topic))
    subject_repo = Mock(get_by_id=Mock(return_value=subject))
    source_repo.save.side_effect = lambda s: s

    use_case = IngestKnowledgeSourceUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    content = "A Constituição é a lei fundamental e suprema de um Estado soberano."
    req = CreateKnowledgeSourceRequest(
        title="Capítulo 1 - Teoria da Constituição",
        content=content,
        content_type="BOOK_CHAPTER",
    )

    res = asyncio.run(use_case.execute(user_id=user_id, topic_id=topic.id, request=req))

    assert res.title == "Capítulo 1 - Teoria da Constituição"
    assert res.topic_id == topic.id
    assert res.topic_ids == [topic.id]
    assert res.content_type == "BOOK_CHAPTER"
    assert res.total_chunks == 0
    assert res.char_count == len(content)
    source_repo.save.assert_called_once()


@pytest.mark.unit
def test_ingest_knowledge_source_multiple_topics_success(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    """Valida ingestão associada a múltiplos temas simultaneamente (N:N)."""
    topic2 = Topic(subject_id=subject.id, name="Direitos Fundamentais")
    source_repo = Mock()
    source_repo.save.side_effect = lambda s: s
    topic_repo = Mock()
    topic_repo.get_by_id.side_effect = lambda tid: topic if tid == topic.id else topic2
    subject_repo = Mock(get_by_id=Mock(return_value=subject))

    use_case = IngestKnowledgeSourceUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )
    req = CreateKnowledgeSourceRequest(
        title="Material Multitemático",
        content="Conteúdo extenso suficiente para ultrapassar vinte caracteres.",
        topic_ids=[topic.id, topic2.id],
    )

    res = asyncio.run(use_case.execute(user_id=user_id, topic_id=None, request=req))
    assert res.topic_ids == [topic.id, topic2.id]
    assert res.topic_id == topic.id


@pytest.mark.unit
@pytest.mark.security
def test_ingest_knowledge_source_sanitizes_html_tags(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    """Valida remoção de tags HTML/scripts maliciosos durante a ingestão de material didático.

    Vulnerabilidade prevenida: Stored Cross-Site Scripting (XSS) via conteúdo de materiais (CWE-79).
    Garantia de segurança: nh3.clean remove todas as tags HTML antes da persistência do raw_text.
    """
    saved_entities: list[KnowledgeSource] = []
    source_repo = Mock()

    def capture_save(source: KnowledgeSource) -> KnowledgeSource:
        saved_entities.append(source)
        return source

    source_repo.save.side_effect = capture_save
    topic_repo = Mock(get_by_id=Mock(return_value=topic))
    subject_repo = Mock(get_by_id=Mock(return_value=subject))

    use_case = IngestKnowledgeSourceUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )
    req = CreateKnowledgeSourceRequest(
        title="Material Sanitizado",
        content="<script>alert(1)</script><p>Conteúdo didático seguro e legítimo para revisão.</p>",
    )

    res = asyncio.run(use_case.execute(user_id=user_id, topic_id=topic.id, request=req))
    assert len(saved_entities) == 1
    assert "<script>" not in saved_entities[0].raw_text
    assert "<p>" not in saved_entities[0].raw_text
    assert saved_entities[0].raw_text == "Conteúdo didático seguro e legítimo para revisão."
    assert res.char_count == len("Conteúdo didático seguro e legítimo para revisão.")


@pytest.mark.unit
def test_ingest_knowledge_source_no_topics_error(user_id: UUID) -> None:
    """Rejeita ingestão quando nenhum tema é informado em topic_ids nem topic_id."""
    use_case = IngestKnowledgeSourceUseCase(
        source_repo=Mock(),
        topic_repo=Mock(),
        subject_repo=Mock(),
    )
    req = CreateKnowledgeSourceRequest(
        title="Material",
        content="Texto com mais de vinte caracteres para passar na validação de tamanho.",
        topic_ids=[],
    )
    with pytest.raises(DomainValidationError, match="associado a pelo menos 1 tema"):
        asyncio.run(use_case.execute(user_id=user_id, topic_id=None, request=req))


@pytest.mark.unit
def test_ingest_knowledge_source_topic_not_found(user_id: UUID) -> None:
    """Dispara EntityNotFoundError quando algum tema alvo não existe."""
    use_case = IngestKnowledgeSourceUseCase(
        source_repo=Mock(),
        topic_repo=Mock(get_by_id=Mock(return_value=None)),
        subject_repo=Mock(),
    )
    req = CreateKnowledgeSourceRequest(
        title="Material",
        content="Texto com mais de vinte caracteres válidos.",
    )
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        asyncio.run(use_case.execute(user_id=user_id, topic_id=uuid4(), request=req))


@pytest.mark.unit
def test_ingest_knowledge_source_ownership_error(
    other_user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    """Rejeita ingestão por usuário que não é proprietário da matéria."""
    use_case = IngestKnowledgeSourceUseCase(
        source_repo=Mock(),
        topic_repo=Mock(get_by_id=Mock(return_value=topic)),
        subject_repo=Mock(get_by_id=Mock(return_value=subject)),
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
    """Rejeita conteúdo com menos de 20 caracteres úteis após sanitização."""
    use_case = IngestKnowledgeSourceUseCase(
        source_repo=Mock(),
        topic_repo=Mock(get_by_id=Mock(return_value=topic)),
        subject_repo=Mock(get_by_id=Mock(return_value=subject)),
    )
    req = CreateKnowledgeSourceRequest(title="Muito Curto", content="<b>Curto</b>")
    with pytest.raises(EmptyKnowledgeContentError, match="pelo menos 20 caracteres úteis"):
        asyncio.run(use_case.execute(user_id=user_id, topic_id=topic.id, request=req))


@pytest.mark.unit
def test_link_knowledge_source_to_topics_success(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    """Valida atualização da lista de temas vinculados a uma fonte existente."""
    topic2 = Topic(subject_id=subject.id, name="Direitos Sociais")
    source = KnowledgeSource(
        title="Doutrina Geral",
        content_type="TEXT",
        topic_ids=(topic.id,),
        raw_text="Texto preservado da fonte original.",
        char_count=35,
    )

    source_repo = Mock(get_by_id=Mock(return_value=source))
    source_repo.save.side_effect = lambda s: s
    topic_repo = Mock()
    topic_repo.get_by_id.side_effect = lambda tid: topic if tid == topic.id else topic2
    subject_repo = Mock(get_by_id=Mock(return_value=subject))

    use_case = LinkKnowledgeSourceToTopicsUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    req = LinkKnowledgeSourceRequest(
        source_id=source.id,
        topic_ids=[topic.id, topic2.id],
    )
    res = asyncio.run(use_case.execute(user_id=user_id, request=req))

    assert res.id == source.id
    assert set(res.topic_ids) == {topic.id, topic2.id}
    source_repo.save.assert_called_once()


@pytest.mark.unit
def test_link_knowledge_source_empty_topics_error(user_id: UUID) -> None:
    """Rejeita atualização de vínculo com lista vazia de topic_ids."""
    source = KnowledgeSource(title="Doutrina", content_type="TEXT", topic_ids=(uuid4(),))
    use_case = LinkKnowledgeSourceToTopicsUseCase(
        source_repo=Mock(get_by_id=Mock(return_value=source)),
        topic_repo=Mock(),
        subject_repo=Mock(),
    )
    req = LinkKnowledgeSourceRequest(source_id=source.id, topic_ids=[])
    with pytest.raises(DomainValidationError, match="pelo menos 1 tema"):
        asyncio.run(use_case.execute(user_id=user_id, request=req))


@pytest.mark.unit
def test_link_knowledge_source_not_found_error(user_id: UUID) -> None:
    """Dispara KnowledgeSourceNotFoundError quando a fonte não existe."""
    use_case = LinkKnowledgeSourceToTopicsUseCase(
        source_repo=Mock(get_by_id=Mock(return_value=None)),
        topic_repo=Mock(),
        subject_repo=Mock(),
    )
    req = LinkKnowledgeSourceRequest(source_id=uuid4(), topic_ids=[uuid4()])
    with pytest.raises(KnowledgeSourceNotFoundError, match="Fonte de conhecimento não encontrada"):
        asyncio.run(use_case.execute(user_id=user_id, request=req))


@pytest.mark.unit
def test_link_knowledge_source_topic_not_found_error(
    user_id: UUID,
    topic: Topic,
) -> None:
    """Dispara EntityNotFoundError quando um dos temas informados não existe."""
    source = KnowledgeSource(title="Doutrina Geral", content_type="TEXT", topic_ids=(topic.id,))
    use_case = LinkKnowledgeSourceToTopicsUseCase(
        source_repo=Mock(get_by_id=Mock(return_value=source)),
        topic_repo=Mock(get_by_id=Mock(return_value=None)),
        subject_repo=Mock(),
    )
    req = LinkKnowledgeSourceRequest(source_id=source.id, topic_ids=[uuid4()])
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        asyncio.run(use_case.execute(user_id=user_id, request=req))


@pytest.mark.unit
def test_link_knowledge_source_ownership_error(
    other_user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    """Rejeita vínculo de temas por usuário sem posse sobre a matéria."""
    source = KnowledgeSource(title="Doutrina Geral", content_type="TEXT", topic_ids=(topic.id,))
    use_case = LinkKnowledgeSourceToTopicsUseCase(
        source_repo=Mock(get_by_id=Mock(return_value=source)),
        topic_repo=Mock(get_by_id=Mock(return_value=topic)),
        subject_repo=Mock(get_by_id=Mock(return_value=subject)),
    )
    req = LinkKnowledgeSourceRequest(source_id=source.id, topic_ids=[topic.id])
    with pytest.raises(ResourceOwnershipError, match="Apenas o proprietário da matéria"):
        asyncio.run(use_case.execute(user_id=other_user_id, request=req))


@pytest.mark.unit
def test_get_topic_knowledge_sources_success_owner_and_public(
    user_id: UUID,
    other_user_id: UUID,
    public_subject: Subject,
) -> None:
    """Permite listagem de fontes para o proprietário e para terceiros em matéria pública."""
    pub_topic = Topic(subject_id=public_subject.id, name="Licitações")
    s1 = KnowledgeSource(
        topic_id=pub_topic.id,
        title="Manual Constitucional",
        total_chunks=0,
        char_count=5000,
    )
    source_repo = Mock(list_by_topic=Mock(return_value=[s1]))
    topic_repo = Mock(get_by_id=Mock(return_value=pub_topic))
    subject_repo = Mock(get_by_id=Mock(return_value=public_subject))

    use_case = GetTopicKnowledgeSourcesUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    for requester in (user_id, other_user_id):
        sources = asyncio.run(use_case.execute(user_id=requester, topic_id=pub_topic.id))
        assert len(sources) == 1
        assert sources[0].title == "Manual Constitucional"
        assert sources[0].topic_ids == [pub_topic.id]


@pytest.mark.unit
def test_get_topic_knowledge_sources_topic_not_found(user_id: UUID) -> None:
    """Dispara EntityNotFoundError quando o tema consultado não existe."""
    use_case = GetTopicKnowledgeSourcesUseCase(
        source_repo=Mock(),
        topic_repo=Mock(get_by_id=Mock(return_value=None)),
        subject_repo=Mock(),
    )
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        asyncio.run(use_case.execute(user_id=user_id, topic_id=uuid4()))


@pytest.mark.unit
def test_get_topic_knowledge_sources_private_subject_forbidden(
    other_user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    """Rejeita listagem de materiais de matéria privada por outro usuário."""
    use_case = GetTopicKnowledgeSourcesUseCase(
        source_repo=Mock(),
        topic_repo=Mock(get_by_id=Mock(return_value=topic)),
        subject_repo=Mock(get_by_id=Mock(return_value=subject)),
    )
    with pytest.raises(ResourceOwnershipError, match="Sem permissão para visualizar o tema"):
        asyncio.run(use_case.execute(user_id=other_user_id, topic_id=topic.id))


@pytest.mark.unit
def test_delete_knowledge_source_success(
    user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    """Valida remoção bem-sucedida de material didático pelo proprietário."""
    source_repo = Mock()
    topic_repo = Mock(get_by_id=Mock(return_value=topic))
    subject_repo = Mock(get_by_id=Mock(return_value=subject))

    s1 = KnowledgeSource(topic_id=topic.id, title="Para Deletar")
    source_repo.get_by_id.return_value = s1

    use_case = DeleteKnowledgeSourceUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    asyncio.run(use_case.execute(user_id=user_id, source_id=s1.id))
    source_repo.delete.assert_called_once_with(s1.id)


@pytest.mark.unit
def test_delete_knowledge_source_not_found(user_id: UUID) -> None:
    """Dispara KnowledgeSourceNotFoundError ao tentar excluir fonte inexistente."""
    use_case = DeleteKnowledgeSourceUseCase(
        source_repo=Mock(get_by_id=Mock(return_value=None)),
        topic_repo=Mock(),
        subject_repo=Mock(),
    )
    with pytest.raises(KnowledgeSourceNotFoundError, match="Fonte de conhecimento não encontrada"):
        asyncio.run(use_case.execute(user_id=user_id, source_id=uuid4()))


@pytest.mark.unit
def test_delete_knowledge_source_topic_not_found(user_id: UUID) -> None:
    """Dispara EntityNotFoundError se o tema vinculado à fonte não existir."""
    source = KnowledgeSource(topic_id=uuid4(), title="Livro")
    use_case = DeleteKnowledgeSourceUseCase(
        source_repo=Mock(get_by_id=Mock(return_value=source)),
        topic_repo=Mock(get_by_id=Mock(return_value=None)),
        subject_repo=Mock(),
    )
    with pytest.raises(EntityNotFoundError, match="Tema não encontrado"):
        asyncio.run(use_case.execute(user_id=user_id, source_id=source.id))


@pytest.mark.unit
def test_delete_knowledge_source_ownership_error(
    other_user_id: UUID,
    subject: Subject,
    topic: Topic,
) -> None:
    """Rejeita exclusão de material didático por usuário que não é dono da matéria."""
    source = KnowledgeSource(topic_id=topic.id, title="Livro Protegido")
    use_case = DeleteKnowledgeSourceUseCase(
        source_repo=Mock(get_by_id=Mock(return_value=source)),
        topic_repo=Mock(get_by_id=Mock(return_value=topic)),
        subject_repo=Mock(get_by_id=Mock(return_value=subject)),
    )
    with pytest.raises(ResourceOwnershipError, match="Apenas o proprietário pode excluir"):
        asyncio.run(use_case.execute(user_id=other_user_id, source_id=source.id))
