"""Testes unitários dos controladores REST de materiais didáticos locais."""

import asyncio
import io
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from src.adapters.api.knowledge_controllers import (
    IngestSourceRequest,
    LinkTopicsRequest,
    delete_knowledge_source,
    extract_file_text,
    ingest_knowledge_source,
    link_knowledge_source_topics,
    list_topic_knowledge_sources,
)
from src.application.dto.knowledge_dto import KnowledgeSourceResponse
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    EmptyKnowledgeContentError,
    EntityNotFoundError,
    KnowledgeSourceNotFoundError,
    ResourceOwnershipError,
)


@pytest.fixture
def user() -> User:
    return User(
        id=uuid4(),
        google_sub="local:unit@test.com",
        email="unit@test.com",
        name="Unit User",
    )


@pytest.mark.unit
def test_ingest_knowledge_source_controller_success(user: User) -> None:
    """Valida retorno 201 serializado e commit na ingestão bem-sucedida."""
    db = Mock()
    topic_id = uuid4()
    source_id = uuid4()
    payload = IngestSourceRequest(
        title="Apostila Constitucional",
        content="Conteúdo constitucional com mais de vinte caracteres válidos.",
        content_type="TEXT",
    )
    expected = KnowledgeSourceResponse(
        id=source_id,
        topic_id=topic_id,
        title=payload.title,
        content_type="TEXT",
        total_chunks=0,
        char_count=len(payload.content),
        created_at="2026-10-12",
        topic_ids=[topic_id],
    )

    with patch(
        "src.adapters.api.knowledge_controllers.IngestKnowledgeSourceUseCase.execute",
        new=AsyncMock(return_value=expected),
    ):
        res = asyncio.run(
            ingest_knowledge_source(topic_id=topic_id, payload=payload, db=db, user=user)
        )

    assert res["id"] == str(source_id)
    assert res["topic_id"] == str(topic_id)
    assert res["topic_ids"] == [str(topic_id)]
    assert res["title"] == "Apostila Constitucional"
    db.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (EntityNotFoundError("Tema não encontrado"), 404),
        (ResourceOwnershipError("Sem permissão"), 403),
        (EmptyKnowledgeContentError("Conteúdo curto"), 400),
        (DomainValidationError("Validação falhou"), 400),
    ],
)
def test_ingest_knowledge_source_controller_error_mapping(
    user: User, exc: Exception, expected_status: int
) -> None:
    """Valida mapeamento de exceções para HTTP 404/403/400 com rollback no banco."""
    db = Mock()
    payload = IngestSourceRequest(
        title="Apostila",
        content="Conteúdo constitucional com mais de vinte caracteres válidos.",
    )
    with patch(
        "src.adapters.api.knowledge_controllers.IngestKnowledgeSourceUseCase.execute",
        new=AsyncMock(side_effect=exc),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                ingest_knowledge_source(topic_id=uuid4(), payload=payload, db=db, user=user)
            )
    assert exc_info.value.status_code == expected_status
    db.rollback.assert_called_once()


@pytest.mark.unit
def test_link_knowledge_source_topics_controller_success(user: User) -> None:
    """Valida atualização de vínculo N:N de temas e commit."""
    db = Mock()
    source_id = uuid4()
    t1, t2 = uuid4(), uuid4()
    payload = LinkTopicsRequest(topic_ids=[t1, t2])
    expected = KnowledgeSourceResponse(
        id=source_id,
        topic_id=t1,
        title="Doutrina",
        content_type="TEXT",
        total_chunks=0,
        char_count=200,
        created_at="2026-10-12",
        topic_ids=[t1, t2],
    )

    with patch(
        "src.adapters.api.knowledge_controllers.LinkKnowledgeSourceToTopicsUseCase.execute",
        new=AsyncMock(return_value=expected),
    ):
        res = asyncio.run(
            link_knowledge_source_topics(source_id=source_id, payload=payload, db=db, user=user)
        )

    assert res["id"] == str(source_id)
    assert res["topic_ids"] == [str(t1), str(t2)]
    db.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (KnowledgeSourceNotFoundError("Fonte não encontrada"), 404),
        (EntityNotFoundError("Tema não encontrado"), 404),
        (ResourceOwnershipError("Sem permissão"), 403),
        (DomainValidationError("Lista inválida"), 400),
    ],
)
def test_link_knowledge_source_topics_controller_error_mapping(
    user: User, exc: Exception, expected_status: int
) -> None:
    """Valida mapeamento de exceções para HTTP 404/403/400 com rollback em link_topics."""
    db = Mock()
    payload = LinkTopicsRequest(topic_ids=[uuid4()])
    with patch(
        "src.adapters.api.knowledge_controllers.LinkKnowledgeSourceToTopicsUseCase.execute",
        new=AsyncMock(side_effect=exc),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                link_knowledge_source_topics(source_id=uuid4(), payload=payload, db=db, user=user)
            )
    assert exc_info.value.status_code == expected_status
    db.rollback.assert_called_once()


@pytest.mark.unit
def test_extract_file_text_controller_success(user: User) -> None:
    """Valida extração de arquivo TXT e cálculo de preview/chunk_estimate em /knowledge/extract-file."""
    text = "Conteúdo didático extraído com sucesso para estudo local."
    upload = UploadFile(
        file=io.BytesIO(text.encode("utf-8")),
        filename="resumo.txt",
        headers=Headers({"content-type": "text/plain"}),
    )

    res = asyncio.run(extract_file_text(file=upload, user=user))

    assert res["filename"] == "resumo.txt"
    assert res["extracted_text"] == text
    assert res["text_preview"] == text[:2000]
    assert res["char_count"] == len(text)
    assert res["chunk_estimate"] == 1


@pytest.mark.unit
def test_extract_file_text_controller_payload_too_large_413(user: User) -> None:
    """Rejeita upload acima de 15 MB com HTTP 413."""
    oversized = b"a" * (15 * 1024 * 1024 + 1)
    upload = UploadFile(
        file=io.BytesIO(oversized),
        filename="gigante.txt",
        headers=Headers({"content-type": "text/plain"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(extract_file_text(file=upload, user=user))
    assert exc_info.value.status_code == 413


@pytest.mark.unit
def test_extract_file_text_controller_domain_validation_error_400(user: User) -> None:
    """Mapeia DomainValidationError na extração de arquivo para HTTP 400."""
    upload = UploadFile(
        file=io.BytesIO(b"binary"),
        filename="script.exe",
        headers=Headers({"content-type": "application/octet-stream"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(extract_file_text(file=upload, user=user))
    assert exc_info.value.status_code == 400


@pytest.mark.unit
def test_list_topic_knowledge_sources_controller_success(user: User) -> None:
    """Valida serialização da listagem de materiais didáticos de um tema."""
    db = Mock()
    topic_id = uuid4()
    source_id = uuid4()
    expected = [
        KnowledgeSourceResponse(
            id=source_id,
            topic_id=topic_id,
            title="Resumo 1",
            content_type="TEXT",
            total_chunks=0,
            char_count=120,
            created_at="2026-10-12",
            topic_ids=[topic_id],
        )
    ]

    with patch(
        "src.adapters.api.knowledge_controllers.GetTopicKnowledgeSourcesUseCase.execute",
        new=AsyncMock(return_value=expected),
    ):
        res = asyncio.run(list_topic_knowledge_sources(topic_id=topic_id, db=db, user=user))

    assert len(res) == 1
    assert res[0]["id"] == str(source_id)
    assert res[0]["topic_ids"] == [str(topic_id)]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (EntityNotFoundError("Tema não encontrado"), 404),
        (ResourceOwnershipError("Sem permissão"), 403),
    ],
)
def test_list_topic_knowledge_sources_controller_error_mapping(
    user: User, exc: Exception, expected_status: int
) -> None:
    """Valida mapeamento de erros 404 e 403 na listagem de materiais do tema."""
    db = Mock()
    with patch(
        "src.adapters.api.knowledge_controllers.GetTopicKnowledgeSourcesUseCase.execute",
        new=AsyncMock(side_effect=exc),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(list_topic_knowledge_sources(topic_id=uuid4(), db=db, user=user))
    assert exc_info.value.status_code == expected_status


@pytest.mark.unit
def test_delete_knowledge_source_controller_success(user: User) -> None:
    """Valida exclusão bem-sucedida com commit no banco."""
    db = Mock()
    with patch(
        "src.adapters.api.knowledge_controllers.DeleteKnowledgeSourceUseCase.execute",
        new=AsyncMock(return_value=None),
    ):
        asyncio.run(delete_knowledge_source(source_id=uuid4(), db=db, user=user))
    db.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (KnowledgeSourceNotFoundError("Fonte não encontrada"), 404),
        (EntityNotFoundError("Tema não encontrado"), 404),
        (ResourceOwnershipError("Sem permissão"), 403),
    ],
)
def test_delete_knowledge_source_controller_error_mapping(
    user: User, exc: Exception, expected_status: int
) -> None:
    """Valida mapeamento de exceções para 404/403 com rollback na exclusão de fonte."""
    db = Mock()
    with patch(
        "src.adapters.api.knowledge_controllers.DeleteKnowledgeSourceUseCase.execute",
        new=AsyncMock(side_effect=exc),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(delete_knowledge_source(source_id=uuid4(), db=db, user=user))
    assert exc_info.value.status_code == expected_status
    db.rollback.assert_called_once()
