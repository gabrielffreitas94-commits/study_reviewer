"""Testes de integração para os controladores Web e templates de Biblioteca de Materiais (Camada 3)."""

from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
        google_sub="local:know.web@studyreviewer.local",
        email="know.web@studyreviewer.local",
        name="Web Knowledge User",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="local:other.k@studyreviewer.local",
        email="other.k@studyreviewer.local",
        name="Other User",
    )


@pytest.fixture
def db_engine() -> Generator[Any, None, None]:
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
def client(db_engine: Any, test_user: User, other_user: User) -> Generator[TestClient, None, None]:
    TestingSession = sessionmaker(bind=db_engine)

    with TestingSession() as session:
        u_repo = SqlAlchemyUserRepository(session)
        u_repo.save(test_user)
        u_repo.save(other_user)

    def override_get_db() -> Generator[Session, None, None]:
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
    """Valida estado vazio da tela /knowledge/manage quando não há matérias."""
    resp = client.get("/knowledge/manage")
    assert resp.status_code == 200
    assert "Biblioteca de Materiais" in resp.text
    assert "Nenhuma Matéria ou Tema Cadastrado" in resp.text


@pytest.mark.integration
def test_manage_knowledge_view_with_subjects(
    client: TestClient,
    db_engine: Any,
    test_user: User,
) -> None:
    """Valida exibição do formulário de cadastro de material com matérias e temas."""
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
    assert "Cadastrar Novo Material de Estudo" in resp.text


@pytest.mark.integration
def test_create_knowledge_source_web_text_success(
    client: TestClient,
    db_engine: Any,
    test_user: User,
) -> None:
    """Valida cadastro de material de texto local via POST /knowledge/manage."""
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

    with TestingSession() as session:
        sources = SqlAlchemyKnowledgeSourceRepository(session).list_by_topic(topic_id)
        assert len(sources) == 1
        assert sources[0].title == "Apostila de Sociedades"
        assert "quotas" in sources[0].raw_text


@pytest.mark.integration
def test_create_knowledge_source_web_file_upload_success(
    client: TestClient,
    db_engine: Any,
    test_user: User,
) -> None:
    """Valida upload de arquivo .txt via POST /knowledge/manage com extração local."""
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

    with TestingSession() as session:
        sources = SqlAlchemyKnowledgeSourceRepository(session).list_by_topic(topic_id)
        assert len(sources) == 1
        assert sources[0].content_type == "FILE"
        assert "fato gerador" in sources[0].raw_text


@pytest.mark.integration
def test_create_knowledge_source_web_missing_topics_error(client: TestClient) -> None:
    """Garante redirecionamento com erro ao tentar salvar material sem tema selecionado."""
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
    """Valida exclusão de material didático via POST /knowledge/manage/{id}/delete."""
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
            raw_text="Consolidação das Leis do Trabalho e direitos fundamentais.",
            char_count=58,
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
    """Garante rejeição de arquivos acima de 15MB no formulário web."""
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
    """Garante rejeição de extensão não suportada no formulário web."""
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
) -> None:
    """Ignora UUIDs malformados em topic_ids quando há ao menos um tema válido."""
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
    """Garante redirecionamento com erro quando conteúdo possui menos de 20 caracteres úteis."""
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
    """Garante redirecionamento com erro ao tentar excluir fonte inexistente."""
    resp = client.post(f"/knowledge/manage/{uuid4()}/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
