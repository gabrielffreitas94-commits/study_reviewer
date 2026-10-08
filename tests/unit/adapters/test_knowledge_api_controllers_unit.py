"""Testes unitários dos controladores de API de conhecimento (Sprint 07)."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.adapters.api.knowledge_controllers import (
    ValidateQuestionPayload,
    delete_knowledge_source,
    list_topic_knowledge_sources,
    validate_question_grounding,
)
from src.domain.entities import User
from src.domain.exceptions import (
    EntityNotFoundError,
    ResourceOwnershipError,
)


@pytest.fixture
def user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-unit-1",
        email="unit@test.com",
        name="Unit User",
    )


@pytest.mark.unit
def test_delete_knowledge_source_topic_entity_not_found(user: User) -> None:
    db = Mock()
    source_id = uuid4()
    with patch(
        "src.adapters.api.knowledge_controllers.DeleteKnowledgeSourceUseCase.execute",
        new=AsyncMock(side_effect=EntityNotFoundError("Tema não encontrado")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(delete_knowledge_source(source_id=source_id, db=db, user=user))
        assert exc_info.value.status_code == 404
        db.rollback.assert_called_once()


@pytest.mark.unit
def test_delete_knowledge_source_ownership_error(user: User) -> None:
    db = Mock()
    source_id = uuid4()
    with patch(
        "src.adapters.api.knowledge_controllers.DeleteKnowledgeSourceUseCase.execute",
        new=AsyncMock(side_effect=ResourceOwnershipError("Sem permissão")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(delete_knowledge_source(source_id=source_id, db=db, user=user))
        assert exc_info.value.status_code == 403
        db.rollback.assert_called_once()


@pytest.mark.unit
def test_list_topic_knowledge_sources_ownership_error(user: User) -> None:
    db = Mock()
    topic_id = uuid4()
    with patch(
        "src.adapters.api.knowledge_controllers.GetTopicKnowledgeSourcesUseCase.execute",
        new=AsyncMock(side_effect=ResourceOwnershipError("Sem permissão")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(list_topic_knowledge_sources(topic_id=topic_id, db=db, user=user))
        assert exc_info.value.status_code == 403


@pytest.mark.unit
def test_validate_question_grounding_entity_not_found(user: User) -> None:
    db = Mock()
    topic_id = uuid4()
    payload = ValidateQuestionPayload(prompt="P", expected_answer="R")
    with patch(
        "src.adapters.api.knowledge_controllers.ValidateQuestionWithKnowledgeUseCase.execute",
        new=AsyncMock(side_effect=EntityNotFoundError("Tema não encontrado")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                validate_question_grounding(topic_id=topic_id, payload=payload, db=db, user=user)
            )
        assert exc_info.value.status_code == 404


@pytest.mark.unit
def test_validate_question_grounding_ownership_error(user: User) -> None:
    db = Mock()
    topic_id = uuid4()
    payload = ValidateQuestionPayload(prompt="P", expected_answer="R")
    with patch(
        "src.adapters.api.knowledge_controllers.ValidateQuestionWithKnowledgeUseCase.execute",
        new=AsyncMock(side_effect=ResourceOwnershipError("Sem permissão")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                validate_question_grounding(topic_id=topic_id, payload=payload, db=db, user=user)
            )
        assert exc_info.value.status_code == 403
