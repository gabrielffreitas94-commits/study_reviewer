"""Testes de integração para os controladores REST de Base de Conhecimento e RAG (Sprint 07)."""

from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyKnowledgeChunkRepository,
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
        google_sub="sub-api-know-1",
        email="know.user@studyreviewer.local",
        name="Knowledge Owner",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-api-know-2",
        email="other.know@studyreviewer.local",
        name="Other Knowledge User",
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
def test_knowledge_api_full_lifecycle(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Direito Administrativo", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Atos Administrativos")
    top_repo.save(topic)
    db_session.commit()

    # 1. Ingerir material didático
    ingest_payload = {
        "title": "Manual de Atos Administrativos",
        "content": (
            "Os atos administrativos possuem atributos como presunção de legitimidade, "
            "imperatividade, autoexecutoriedade e tipicidade segundo a doutrina clássica."
        ),
        "content_type": "SUMMARY",
    }
    resp = client.post(f"/api/v1/topics/{topic.id}/knowledge", json=ingest_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Manual de Atos Administrativos"
    assert data["total_chunks"] >= 1
    source_id = data["id"]

    # 2. Listar materiais do tema
    resp_list = client.get(f"/api/v1/topics/{topic.id}/knowledge")
    assert resp_list.status_code == 200
    sources = resp_list.json()
    assert len(sources) == 1
    assert sources[0]["id"] == source_id

    # 3. Validar questão grounded
    val_payload = {
        "prompt": "Quais são os atributos do ato administrativo?",
        "expected_answer": (
            "Presunção de legitimidade, imperatividade, autoexecutoriedade e tipicidade."
        ),
    }
    resp_val = client.post(f"/api/v1/topics/{topic.id}/validate-question", json=val_payload)
    assert resp_val.status_code == 200
    val_data = resp_val.json()
    assert val_data["is_grounded"] is True
    assert val_data["confidence_score"] >= 0.85
    assert len(val_data["evidence_chunk_ids"]) >= 1

    # 4. Deletar material didático
    resp_del = client.delete(f"/api/v1/knowledge/{source_id}")
    assert resp_del.status_code == 204

    # 5. Listar novamente (deve estar vazio)
    resp_list_after = client.get(f"/api/v1/topics/{topic.id}/knowledge")
    assert resp_list_after.status_code == 200
    assert len(resp_list_after.json()) == 0


@pytest.mark.integration
def test_knowledge_api_validation_errors_and_not_found(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Direito", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Geral")
    top_repo.save(topic)
    db_session.commit()

    # Conteúdo com menos de 20 caracteres brutos -> 422 (Pydantic)
    resp_short_pydantic = client.post(
        f"/api/v1/topics/{topic.id}/knowledge",
        json={"title": "Curto", "content": "menos de vinte"},
    )
    assert resp_short_pydantic.status_code == 422

    # Conteúdo com mais de 20 caracteres brutos que após sanitização fica < 20 úteis -> 400
    resp_short_domain = client.post(
        f"/api/v1/topics/{topic.id}/knowledge",
        json={"title": "Válido", "content": "   <p>   curto de texto   </p>   "},
    )
    assert resp_short_domain.status_code == 400
    assert "pelo menos 20 caracteres úteis" in resp_short_domain.json()["detail"]

    # Tema inexistente -> 404
    fake_topic_id = uuid4()
    resp_404 = client.post(
        f"/api/v1/topics/{fake_topic_id}/knowledge",
        json={"title": "Válido", "content": "Conteúdo com mais de vinte caracteres suficientes."},
    )
    assert resp_404.status_code == 404

    # Listagem de tema inexistente -> 404
    resp_list_404 = client.get(f"/api/v1/topics/{fake_topic_id}/knowledge")
    assert resp_list_404.status_code == 404

    # Validação em tema inexistente -> 404
    resp_val_404 = client.post(
        f"/api/v1/topics/{fake_topic_id}/validate-question",
        json={"prompt": "P", "expected_answer": "R"},
    )
    assert resp_val_404.status_code == 404

    # Fonte inexistente no delete -> 404
    fake_source_id = uuid4()
    resp_del_404 = client.delete(f"/api/v1/knowledge/{fake_source_id}")
    assert resp_del_404.status_code == 404


@pytest.mark.security
def test_security_knowledge_idor_prevention(
    client: TestClient,
    db_session: Session,
    other_user: User,
) -> None:
    """Vulnerabilidade prevenida: IDOR (Insecure Direct Object Reference).

    Garantia de segurança: Um usuário não pode cadastrar, listar nem excluir
    materiais didáticos de matérias privadas pertencentes a outros usuários.
    """
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db_session)

    user_repo.save(other_user)
    other_subj = Subject(name="Privado do Outro", owner_id=other_user.id, is_public=False)
    subj_repo.save(other_subj)
    other_topic = Topic(subject_id=other_subj.id, name="Segredo")
    top_repo.save(other_topic)

    other_source = KnowledgeSource(topic_id=other_topic.id, title="Material Privado")
    source_repo.save(other_source)
    db_session.commit()

    # 1. Tentativa de ingestão no tema alheio -> 403
    resp_ingest = client.post(
        f"/api/v1/topics/{other_topic.id}/knowledge",
        json={"title": "Hack", "content": "Tentativa de injeção de conhecimento no tema alheio."},
    )
    assert resp_ingest.status_code == 403

    # 2. Tentativa de listagem do tema privado alheio -> 403
    resp_list = client.get(f"/api/v1/topics/{other_topic.id}/knowledge")
    assert resp_list.status_code == 403

    # 3. Tentativa de deleção da fonte alheia -> 403
    resp_del = client.delete(f"/api/v1/knowledge/{other_source.id}")
    assert resp_del.status_code == 403

    # 4. Tentativa de validação no tema privado alheio -> 403
    resp_val_idor = client.post(
        f"/api/v1/topics/{other_topic.id}/validate-question",
        json={"prompt": "P", "expected_answer": "R"},
    )
    assert resp_val_idor.status_code == 403


@pytest.mark.security
def test_security_knowledge_content_sanitization(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    """Vulnerabilidade prevenida: Stored Cross-Site Scripting (XSS) e HTML Injection.

    Garantia de segurança: Tags HTML perigosas como <script>, <iframe> e manipuladores
    de eventos (onload, onclick) são sumariamente expurgadas antes da fragmentação e persistência.
    """
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    chunk_repo = SqlAlchemyKnowledgeChunkRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Segurança", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Testes de XSS")
    top_repo.save(topic)
    db_session.commit()

    malicious_payload = {
        "title": "Apostila com Script",
        "content": (
            "Texto legítimo com conteúdo acadêmico suficiente. "
            "<script>alert('XSS Exploit')</script>"
            "<img src=x onerror=alert(1)>"
            "Mais texto explicativo para passar na validação de tamanho mínimo."
        ),
        "content_type": "TEXT",
    }

    resp = client.post(f"/api/v1/topics/{topic.id}/knowledge", json=malicious_payload)
    assert resp.status_code == 201

    chunks = chunk_repo.list_by_topic(topic.id)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert "<script>" not in chunk.content
        assert "onerror" not in chunk.content
        assert "alert(" not in chunk.content


@pytest.mark.integration
def test_knowledge_api_extract_file_endpoint(client: TestClient) -> None:
    sample_text = "Texto de teste para validação de extração via upload multipart."
    files = {"file": ("documento.txt", sample_text.encode("utf-8"), "text/plain")}
    resp = client.post("/api/v1/knowledge/extract-file", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "documento.txt"
    assert data["char_count"] == len(sample_text)
    assert "Texto de teste" in data["text_preview"]

    # Arquivo vazio -> 400
    files_empty = {"file": ("vazio.txt", b"", "text/plain")}
    resp_empty = client.post("/api/v1/knowledge/extract-file", files=files_empty)
    assert resp_empty.status_code == 400


@pytest.mark.integration
def test_knowledge_api_link_topics_endpoint(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Direito Penal", owner_id=test_user.id)
    subj_repo.save(subj)
    t1 = Topic(subject_id=subj.id, name="Teoria do Crime")
    t2 = Topic(subject_id=subj.id, name="Penas")
    top_repo.save(t1)
    top_repo.save(t2)

    source = KnowledgeSource(
        title="Manual de Penal",
        content_type="TEXT",
        topic_ids=(t1.id,),
    )
    source_repo.save(source)
    db_session.commit()

    # Atualiza tópicos para vincular a t1 e t2
    payload = {"topic_ids": [str(t1.id), str(t2.id)]}
    resp = client.put(f"/api/v1/knowledge/{source.id}/topics", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert str(t1.id) in data["topic_ids"]
    assert str(t2.id) in data["topic_ids"]

    # Fonte inexistente -> 404
    resp_404 = client.put(f"/api/v1/knowledge/{uuid4()}/topics", json=payload)
    assert resp_404.status_code == 404

    # Lista vazia de tópicos -> 422 ou 400
    resp_400 = client.put(f"/api/v1/knowledge/{source.id}/topics", json={"topic_ids": []})
    assert resp_400.status_code == 422 or resp_400.status_code == 400

    # Tópico pertencente a outro usuário -> 403 Forbidden
    other_user_id = uuid4()
    other_subj = Subject(name="Direito Militar", owner_id=other_user_id)
    subj_repo.save(other_subj)
    other_topic = Topic(subject_id=other_subj.id, name="CPM")
    top_repo.save(other_topic)
    db_session.commit()

    resp_403 = client.put(
        f"/api/v1/knowledge/{source.id}/topics",
        json={"topic_ids": [str(other_topic.id)]},
    )
    assert resp_403.status_code == 403
    assert "proprietário" in resp_403.json()["detail"]

    # Tópicos duplicados -> 400 Bad Request (DomainValidationError)
    resp_dup_400 = client.put(
        f"/api/v1/knowledge/{source.id}/topics",
        json={"topic_ids": [str(t1.id), str(t1.id)]},
    )
    assert resp_dup_400.status_code == 400
    assert "duplicados" in resp_dup_400.json()["detail"]
