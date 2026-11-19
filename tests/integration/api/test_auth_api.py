"""Testes de integração para os endpoints REST de autenticação local e demo.

Governança multi-tenancy e isolamento anti-IDOR.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.application.ports.auth import ISessionTokenService
from src.domain.entities import Flashcard, Subject, Topic, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_session_service
from src.infrastructure.web.app import app


@pytest.fixture
def api_test_db() -> Generator[sessionmaker[Session], None, None]:
    """Cria banco SQLite em memória isolado."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    yield TestingSession
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def rest_client(api_test_db: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    """TestClient REST limpo sem overrides forçados de get_current_user."""

    def override_get_db() -> Generator[Session, None, None]:
        session = api_test_db()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.integration
def test_api_auth_register_success(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Valida cadastro local via POST /api/v1/auth/register com retorno 201 e Bearer Token."""
    response = rest_client.post(
        "/api/v1/auth/register",
        json={
            "email": "Novo.Estudante@Example.Local",
            "name": "Novo Estudante",
            "password": "SenhaForte123!",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "novo.estudante@example.local"
    assert data["user"]["name"] == "Novo Estudante"

    with api_test_db() as db:
        user = SqlAlchemyUserRepository(db).get_by_email("novo.estudante@example.local")
        assert user is not None
        assert user.google_sub == "local:novo.estudante@example.local"
        assert user.password_hash is not None


@pytest.mark.integration
def test_api_auth_register_duplicate_email_returns_409(rest_client: TestClient) -> None:
    """Garante que tentativa de cadastro com e-mail já existente retorne 409 Conflict."""
    payload = {
        "email": "duplicado@example.local",
        "name": "Primeiro",
        "password": "SenhaForte123!",
    }
    first = rest_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = rest_client.post(
        "/api/v1/auth/register",
        json={
            "email": "DUPLICADO@example.local",
            "name": "Segundo",
            "password": "OutraSenha123!",
        },
    )
    assert second.status_code == 409
    assert "já existe" in second.json()["detail"].lower()


@pytest.mark.integration
def test_api_auth_register_validation_error_returns_400(rest_client: TestClient) -> None:
    """Garante que senha fora da política ou dados inválidos retornem 400 Bad Request."""
    res_short_pw = rest_client.post(
        "/api/v1/auth/register",
        json={
            "email": "valido@example.local",
            "name": "Estudante",
            "password": "123",
        },
    )
    assert res_short_pw.status_code == 400
    assert "8 e 128" in res_short_pw.json()["detail"]

    res_bad_email = rest_client.post(
        "/api/v1/auth/register",
        json={
            "email": "email-invalido",
            "name": "Estudante",
            "password": "SenhaValida123",
        },
    )
    assert res_bad_email.status_code == 400


@pytest.mark.integration
def test_api_auth_login_success(rest_client: TestClient) -> None:
    """Valida autenticação local via POST /api/v1/auth/login com credenciais válidas."""
    reg_res = rest_client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.local",
            "name": "Usuário Login",
            "password": "MinhaSenhaSegura99",
        },
    )
    assert reg_res.status_code == 201

    login_res = rest_client.post(
        "/api/v1/auth/login",
        json={
            "email": "  LOGIN@example.local ",
            "password": "MinhaSenhaSegura99",
        },
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.local"
    assert data["user"]["name"] == "Usuário Login"

    # Valida que o token retornado autentica em /me
    me_res = rest_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "login@example.local"


@pytest.mark.security
def test_api_auth_login_uniform_401_anti_enumeration(rest_client: TestClient) -> None:
    """Rejeita credenciais inválidas com resposta 401 uniforme para impedir enumeração de usuários.

    Vulnerabilidade prevenida: Enumeração de contas (User Enumeration) via mensagens ou códigos
    HTTP divergentes entre e-mail inexistente e senha incorreta.
    Garantia de segurança: Ambos os cenários retornam exatamente HTTP 401 Unauthorized com
    cabeçalho WWW-Authenticate: Bearer e a mesma mensagem genérica 'E-mail ou senha inválidos.'.
    """
    rest_client.post(
        "/api/v1/auth/register",
        json={
            "email": "existente@example.local",
            "name": "Usuário Existente",
            "password": "SenhaCorreta123",
        },
    )

    res_wrong_pw = rest_client.post(
        "/api/v1/auth/login",
        json={"email": "existente@example.local", "password": "SenhaErrada999"},
    )
    res_unknown_email = rest_client.post(
        "/api/v1/auth/login",
        json={"email": "inexistente@example.local", "password": "SenhaErrada999"},
    )

    assert res_wrong_pw.status_code == 401
    assert res_unknown_email.status_code == 401
    assert res_wrong_pw.headers.get("www-authenticate") == "Bearer"
    assert res_unknown_email.headers.get("www-authenticate") == "Bearer"
    assert res_wrong_pw.json()["detail"] == res_unknown_email.json()["detail"]
    assert res_wrong_pw.json()["detail"] == "E-mail ou senha inválidos."


@pytest.mark.integration
def test_api_auth_demo_idempotent(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Valida que POST /api/v1/auth/demo provisiona e reutiliza de forma idempotente a conta Demo."""
    first = rest_client.post("/api/v1/auth/demo")
    assert first.status_code == 200
    d1 = first.json()
    assert d1["token_type"] == "bearer"
    assert d1["user"]["email"] == "demo@studyreviewer.local"
    assert d1["user"]["name"] == "Estudante Demo"

    second = rest_client.post("/api/v1/auth/demo")
    assert second.status_code == 200
    d2 = second.json()
    assert d2["user"]["id"] == d1["user"]["id"]
    assert d2["user"]["email"] == "demo@studyreviewer.local"

    with api_test_db() as db:
        demo_user = SqlAlchemyUserRepository(db).get_by_email("demo@studyreviewer.local")
        assert demo_user is not None
        assert str(demo_user.id) == d1["user"]["id"]


@pytest.mark.security
def test_api_auth_me_with_valid_bearer_token(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Valida resolução de perfil ativo a partir de Bearer token AES-256-GCM legítimo.

    Vulnerabilidade prevenida: Impessoalização de identidade e uso de credenciais forjadas.
    Garantia de segurança: get_current_user decifra o token AES-256-GCM e
    carrega a entidade do banco.
    """
    user = User(google_sub="local:me@test.com", email="me@test.com", name="Meu Perfil")
    with api_test_db() as db:
        SqlAlchemyUserRepository(db).save(user)

    session_service: ISessionTokenService = get_session_service()
    token = session_service.create_session_token(user.id, user.email)

    response = rest_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == "me@test.com"
    assert data["name"] == "Meu Perfil"


@pytest.mark.security
def test_api_auth_me_unauthenticated_or_invalid_token(rest_client: TestClient) -> None:
    """Rejeita requisições à API REST sem token ou com token corrompido/adulterado.

    Vulnerabilidade prevenida: Acesso anônimo ou adulteração de tokens criptográficos.
    Garantia de segurança: Retorna HTTP 401 com cabeçalho WWW-Authenticate: Bearer.
    """
    res_none = rest_client.get("/api/v1/auth/me")
    assert res_none.status_code == 401
    assert res_none.headers.get("www-authenticate") == "Bearer"

    res_invalid = rest_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token-totalmente-invalido"},
    )
    assert res_invalid.status_code == 401


@pytest.mark.security
def test_api_toggle_subject_public_by_owner_and_forbidden_for_intruder(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Verifica alternância de visibilidade de matéria pelo dono e rejeição para terceiros na API.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) em endpoints REST.
    Garantia de segurança: Apenas o owner_id da matéria tem permissão para alterar is_public.
    """
    owner = User(
        google_sub="local:owner.api@test.com", email="owner.api@test.com", name="Owner API"
    )
    intruder = User(
        google_sub="local:intruder.api@test.com", email="intruder.api@test.com", name="Intruder API"
    )

    with api_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(owner)
        user_repo.save(intruder)
        subject_repo = SqlAlchemySubjectRepository(db)
        subject = Subject(name="Direito Penal", owner_id=owner.id, is_public=False)
        subject_repo.save(subject)
        subject_id = subject.id

    session_service: ISessionTokenService = get_session_service()
    owner_token = session_service.create_session_token(owner.id, owner.email)
    intruder_token = session_service.create_session_token(intruder.id, intruder.email)

    res_forbidden = rest_client.post(
        f"/api/v1/subjects/{subject_id}/toggle-public",
        json={"is_public": True},
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert res_forbidden.status_code == 403

    res_success = rest_client.post(
        f"/api/v1/subjects/{subject_id}/toggle-public",
        json={"is_public": True},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_success.status_code == 200
    assert res_success.json()["is_public"] is True

    res_not_found = rest_client.post(
        f"/api/v1/subjects/{uuid4()}/toggle-public",
        json={"is_public": True},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_not_found.status_code == 404


@pytest.mark.security
def test_api_multi_tenancy_isolation_rules(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Valida as regras de isolamento multi-tenant entre matérias privadas e públicas na API.

    Vulnerabilidade prevenida: Vazamento e contaminação de dados entre estudantes
    (IDOR e privacidade).
    Garantia de segurança: Matérias privadas são bloqueadas; matérias públicas
    permitem estudo com sessão individual.
    """
    user_a = User(google_sub="local:a@test.com", email="a@test.com", name="Estudante A")
    user_b = User(google_sub="local:b@test.com", email="b@test.com", name="Estudante B")

    with api_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(user_a)
        user_repo.save(user_b)

        subject_repo = SqlAlchemySubjectRepository(db)
        topic_repo = SqlAlchemyTopicRepository(db)
        card_repo = SqlAlchemyFlashcardRepository(db)

        priv_a = Subject(name="Matéria Privada de A", owner_id=user_a.id, is_public=False)
        subject_repo.save(priv_a)
        top_priv_a = Topic(subject_id=priv_a.id, name="Tema Privado")
        topic_repo.save(top_priv_a)
        card_priv_a = Flashcard(
            topic_id=top_priv_a.id, front="Segredo A", back="Resposta A", position=100
        )
        card_repo.save(card_priv_a)

        pub_a = Subject(name="Matéria Pública de A", owner_id=user_a.id, is_public=True)
        subject_repo.save(pub_a)
        top_pub_a = Topic(subject_id=pub_a.id, name="Tema Público")
        topic_repo.save(top_pub_a)
        card_pub_a = Flashcard(
            topic_id=top_pub_a.id, front="Card Público", back="Resposta Pública", position=100
        )
        card_repo.save(card_pub_a)

    session_service: ISessionTokenService = get_session_service()
    token_b = session_service.create_session_token(user_b.id, user_b.email)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    res_list_topics = rest_client.get(f"/api/v1/subjects/{priv_a.id}/topics", headers=headers_b)
    assert res_list_topics.status_code == 403

    res_study_priv = rest_client.get(
        f"/api/v1/study/next?subject_id={priv_a.id}", headers=headers_b
    )
    assert res_study_priv.status_code == 403

    res_batch_priv = rest_client.get(
        f"/api/v1/study/batch?subject_id={priv_a.id}", headers=headers_b
    )
    assert res_batch_priv.status_code == 403

    res_create_topic = rest_client.post(
        "/api/v1/topics",
        json={"subject_id": str(pub_a.id), "name": "Novo Tema por B"},
        headers=headers_b,
    )
    assert res_create_topic.status_code == 403

    res_create_card = rest_client.post(
        "/api/v1/flashcards",
        json={"topic_id": str(top_pub_a.id), "front": "Card B", "back": "Resp B"},
        headers=headers_b,
    )
    assert res_create_card.status_code == 403

    res_pub_topics = rest_client.get(f"/api/v1/subjects/{pub_a.id}/topics", headers=headers_b)
    assert res_pub_topics.status_code == 200
    assert len(res_pub_topics.json()) == 1

    res_study_pub = rest_client.get(f"/api/v1/study/next?subject_id={pub_a.id}", headers=headers_b)
    assert res_study_pub.status_code == 200
    assert res_study_pub.json()["front"] == "Card Público"


@pytest.mark.integration
def test_api_get_topics_subject_not_found(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Retorna 404 ao tentar listar tópicos de uma matéria inexistente."""
    user = User(google_sub="local:nf@test.com", email="nf@test.com", name="NF User")
    with api_test_db() as db:
        SqlAlchemyUserRepository(db).save(user)

    session_service = get_session_service()
    token = session_service.create_session_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    res = rest_client.get(f"/api/v1/subjects/{uuid4()}/topics", headers=headers)
    assert res.status_code == 404
    assert "Matéria não encontrada" in res.json()["detail"]
