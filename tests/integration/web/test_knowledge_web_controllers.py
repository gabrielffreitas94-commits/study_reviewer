"""Testes de integração para os controladores Web e templates de Base de Conhecimento (Camada 3)."""

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
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import KnowledgeSource, Subject, Topic, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-web-k-1",
        email="know.web@studyreviewer.local",
        name="Web Knowledge User",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-web-k-2",
        email="other.k@studyreviewer.local",
        name="Other User",
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
def client(db_engine: Any, test_user: User, other_user: User) -> Generator[TestClient]:
    TestingSession = sessionmaker(bind=db_engine)

    with TestingSession() as session:
        u_repo = SqlAlchemyUserRepository(session)
        u_repo.save(test_user)
        u_repo.save(other_user)

    def override_get_db() -> Generator[Session]:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.integration
def test_manage_knowledge_view_empty_state(client: TestClient) -> None:
    resp = client.get("/knowledge/manage")
    assert resp.status_code == 200
    assert "Bases de Conhecimento (RAG)" in resp.text
    assert "Nenhuma Matéria ou Tema Cadastrado" in resp.text


@pytest.mark.integration
def test_manage_knowledge_view_with_subjects(
    client: TestClient,
    db_engine: Any,
    test_user: User,
) -> None:
    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        top_repo = SqlAlchemyTopicRepository(session)
        subj = Subject(name="Direito Civil", owner_id=test_user.id)
        subj_repo.save(subj)
        topic = Topic(subject_id=subj.id, name="Parte Geral")
        top_repo.save(topic)
        session.commit()

    resp = client.get("/knowledge/manage")
    assert resp.status_code == 200
    assert "Direito Civil" in resp.text
    assert "Parte Geral" in resp.text
    assert "Cadastrar Novo Material Didático" in resp.text


@pytest.mark.integration
def test_create_knowledge_source_web_text_success(
    client: TestClient,
    db_engine: Any,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        GeminiEmbeddingAdapter,
        "generate_embeddings_batch",
        AsyncMock(side_effect=lambda texts: [[0.1, 0.2, 0.3] for _ in texts]),
    )

    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        top_repo = SqlAlchemyTopicRepository(session)
        subj = Subject(name="Direito Empresarial", owner_id=test_user.id)
        subj_repo.save(subj)
        t1 = Topic(subject_id=subj.id, name="Sociedades Limitadas")
        top_repo.save(t1)
        session.commit()
        topic_id = t1.id

    form_data = {
        "title": "Apostila de Sociedades",
        "content_text": "Sociedade limitada é aquela em que a responsabilidade de cada sócio é restrita ao valor de suas quotas.",
        "topic_ids": [str(topic_id)],
    }
    resp = client.post("/knowledge/manage", data=form_data, follow_redirects=True)
    assert resp.status_code == 200
    assert "Apostila de Sociedades" in resp.text


@pytest.mark.integration
def test_create_knowledge_source_web_file_upload_success(
    client: TestClient,
    db_engine: Any,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        GeminiEmbeddingAdapter,
        "generate_embeddings_batch",
        AsyncMock(side_effect=lambda texts: [[0.1, 0.2, 0.3] for _ in texts]),
    )

    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        top_repo = SqlAlchemyTopicRepository(session)
        subj = Subject(name="Direito Tributário", owner_id=test_user.id)
        subj_repo.save(subj)
        t1 = Topic(subject_id=subj.id, name="Impostos")
        top_repo.save(t1)
        session.commit()
        topic_id = t1.id

    file_content = "Os impostos têm como fato gerador uma situação independente de qualquer atividade estatal específica relativa ao contribuinte."
    files = {"document_file": ("resumo_impostos.txt", file_content.encode("utf-8"), "text/plain")}
    form_data = {
        "title": "Manual de Impostos",
        "content_text": "",
        "topic_ids": [str(topic_id)],
    }

    resp = client.post("/knowledge/manage", data=form_data, files=files, follow_redirects=True)
    assert resp.status_code == 200
    assert "Manual de Impostos" in resp.text


@pytest.mark.integration
def test_create_knowledge_source_web_missing_topics_error(client: TestClient) -> None:
    form_data = {
        "title": "Material Sem Tema",
        "content_text": "Texto explicativo detalhado sobre temas e matérias diversas.",
        "topic_ids": [],
    }
    resp = client.post("/knowledge/manage", data=form_data, follow_redirects=False)
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]


@pytest.mark.integration
def test_delete_knowledge_source_web_success(
    client: TestClient,
    db_engine: Any,
    test_user: User,
) -> None:
    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        top_repo = SqlAlchemyTopicRepository(session)
        source_repo = SqlAlchemyKnowledgeSourceRepository(session)

        subj = Subject(name="Direito do Trabalho", owner_id=test_user.id)
        subj_repo.save(subj)
        topic = Topic(subject_id=subj.id, name="CLT")
        top_repo.save(topic)

        source = KnowledgeSource(
            title="Material CLT",
            content_type="TEXT",
            topic_ids=(topic.id,),
        )
        source_repo.save(source)
        session.commit()
        source_id = source.id

    resp = client.post(f"/knowledge/manage/{source_id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert "Material didático removido com sucesso" in resp.text


@pytest.mark.integration
def test_create_knowledge_source_web_file_too_large_error(
    client: TestClient,
    db_engine: Any,
    test_user: User,
) -> None:
    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        top_repo = SqlAlchemyTopicRepository(session)
        subj = Subject(name="Direito Constitucional", owner_id=test_user.id)
        subj_repo.save(subj)
        t1 = Topic(subject_id=subj.id, name="Controle")
        top_repo.save(t1)
        session.commit()
        topic_id = t1.id

    oversized_bytes = b"A" * (15 * 1024 * 1024 + 10)
    files = {"document_file": ("grande.txt", oversized_bytes, "text/plain")}
    form_data = {
        "title": "Material Gigante",
        "topic_ids": [str(topic_id)],
    }
    resp = client.post("/knowledge/manage", data=form_data, files=files, follow_redirects=False)
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
    assert "15MB" in resp.headers["location"]


@pytest.mark.integration
def test_create_knowledge_source_web_unsupported_file_error(
    client: TestClient,
    db_engine: Any,
    test_user: User,
) -> None:
    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        top_repo = SqlAlchemyTopicRepository(session)
        subj = Subject(name="Direito Penal", owner_id=test_user.id)
        subj_repo.save(subj)
        t1 = Topic(subject_id=subj.id, name="Crimes")
        top_repo.save(t1)
        session.commit()
        topic_id = t1.id

    files = {"document_file": ("executavel.exe", b"binary content", "application/octet-stream")}
    form_data = {
        "title": "Arquivo Inválido",
        "topic_ids": [str(topic_id)],
    }
    resp = client.post("/knowledge/manage", data=form_data, files=files, follow_redirects=False)
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]


@pytest.mark.integration
def test_create_knowledge_source_web_invalid_topic_id_format_skipped(
    client: TestClient,
    db_engine: Any,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        GeminiEmbeddingAdapter,
        "generate_embeddings_batch",
        AsyncMock(side_effect=lambda texts: [[0.1, 0.2, 0.3] for _ in texts]),
    )
    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        top_repo = SqlAlchemyTopicRepository(session)
        subj = Subject(name="Direito Administrativo", owner_id=test_user.id)
        subj_repo.save(subj)
        t1 = Topic(subject_id=subj.id, name="Atos")
        top_repo.save(t1)
        session.commit()
        topic_id = t1.id

    form_data = {
        "title": "Material de Atos Administrativos",
        "content_text": "Os atos administrativos possuem atributos como presunção de legitimidade, imperatividade e autoexecutoriedade.",
        "topic_ids": ["not-a-valid-uuid", str(topic_id)],
    }
    resp = client.post("/knowledge/manage", data=form_data, follow_redirects=True)
    assert resp.status_code == 200
    assert "Material de Atos Administrativos" in resp.text


@pytest.mark.integration
def test_create_knowledge_source_web_short_content_error(
    client: TestClient,
    db_engine: Any,
    test_user: User,
) -> None:
    TestingSession = sessionmaker(bind=db_engine)
    with TestingSession() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        top_repo = SqlAlchemyTopicRepository(session)
        subj = Subject(name="Direito Ambiental", owner_id=test_user.id)
        subj_repo.save(subj)
        t1 = Topic(subject_id=subj.id, name="Princípios")
        top_repo.save(t1)
        session.commit()
        topic_id = t1.id

    form_data = {
        "title": "Material Curto Demais",
        "content_text": "Curto",
        "topic_ids": [str(topic_id)],
    }
    resp = client.post("/knowledge/manage", data=form_data, follow_redirects=False)
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]


@pytest.mark.integration
def test_delete_knowledge_source_web_error(client: TestClient) -> None:
    resp = client.post(f"/knowledge/manage/{uuid4()}/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
