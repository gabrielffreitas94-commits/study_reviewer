"""Testes de integração para a API do Studio Unificado (/api/v1/studio/batch-publish)."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.ai.gemini_adapters import GeminiEmbeddingAdapter
from src.adapters.persistence.repositories import (
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import Subject, Topic, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-studio-1",
        email="studio.user@studyreviewer.local",
        name="Studio User",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-studio-2",
        email="other.studio@studyreviewer.local",
        name="Other Studio User",
    )


@pytest.fixture
def db_engine() -> Generator[Any]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Any) -> Generator[Session]:
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session, test_user: User) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db_session

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.integration
def test_studio_batch_publish_success(
    client: TestClient,
    db_session: Session,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Mock do serviço de embeddings para não bater na API externa durante os testes
    monkeypatch.setattr(
        GeminiEmbeddingAdapter,
        "generate_embeddings_batch",
        AsyncMock(side_effect=lambda texts: [[0.1, 0.2, 0.3] for _ in texts]),
    )

    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Direito Constitucional", owner_id=test_user.id)
    subj_repo.save(subj)
    t1 = Topic(subject_id=subj.id, name="Controle Difuso")
    top_repo.save(t1)
    db_session.commit()

    payload = {
        "subject_id": str(subj.id),
        "new_topics": ["Controle Concentrado", "Ações Constitucionais"],
        "new_sources": [
            {
                "title": "Doutrina Gilmar Mendes",
                "content": "Conteúdo aprofundado sobre controle concentrado de constitucionalidade e ADI/ADC/ADPF.",
                "topic_indices": [0],
                "topic_ids": [str(t1.id)],
                "content_type": "TEXT",
            }
        ],
        "questions": [
            {
                "prompt": "Quem possui legitimidade para propor ADI?",
                "expected_answer": "Os legitimados do art. 103 da Constituição Federal.",
                "topic_index": 0,
            },
            {
                "prompt": "Qual o efeito da decisão no controle difuso?",
                "expected_answer": "Efeito inter partes em regra, salvo resolução do Senado.",
                "topic_id": str(t1.id),
            },
        ],
    }

    resp = client.post("/api/v1/studio/batch-publish", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["subject_id"] == str(subj.id)
    assert data["created_topics_count"] == 2
    assert data["created_sources_count"] == 1
    assert data["created_questions_count"] == 2
    assert len(data["topic_ids"]) == 2
    assert len(data["source_ids"]) == 1
    assert len(data["question_ids"]) == 2

    # Verifica persistência no banco
    all_q = top_repo.list_by_subject(subj.id)
    assert len(all_q) == 3  # 1 existente + 2 novos


@pytest.mark.integration
def test_studio_batch_publish_subject_not_found(client: TestClient) -> None:
    fake_id = uuid4()
    payload = {
        "subject_id": str(fake_id),
        "new_topics": [],
        "new_sources": [],
        "questions": [
            {
                "prompt": "Pergunta de teste?",
                "expected_answer": "Resposta de teste.",
            }
        ],
    }
    resp = client.post("/api/v1/studio/batch-publish", json=payload)
    assert resp.status_code == 404


@pytest.mark.security
def test_studio_batch_publish_idor_prevention(
    client: TestClient,
    db_session: Session,
    other_user: User,
) -> None:
    """Vulnerabilidade prevenida: IDOR (Insecure Direct Object Reference).

    Garantia de segurança: Um usuário não pode publicar temas, bases ou perguntas em matéria pertencente a outro usuário.
    """
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)

    user_repo.save(other_user)
    subj = Subject(name="Matéria Alheia", owner_id=other_user.id)
    subj_repo.save(subj)
    db_session.commit()

    payload = {
        "subject_id": str(subj.id),
        "new_topics": ["Tentativa IDOR"],
        "new_sources": [],
        "questions": [
            {
                "prompt": "Pergunta não autorizada?",
                "expected_answer": "Resposta.",
            }
        ],
    }
    resp = client.post("/api/v1/studio/batch-publish", json=payload)
    assert resp.status_code == 403


@pytest.mark.integration
def test_studio_batch_publish_validation_error(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Matéria Vazia", owner_id=test_user.id)
    subj_repo.save(subj)
    db_session.commit()

    # Sem tópicos existentes e sem novos tópicos -> 400
    payload = {
        "subject_id": str(subj.id),
        "new_topics": [],
        "new_sources": [],
        "questions": [
            {
                "prompt": "Pergunta sem tema?",
                "expected_answer": "Resposta sem tema.",
            }
        ],
    }
    resp = client.post("/api/v1/studio/batch-publish", json=payload)
    assert resp.status_code == 400
