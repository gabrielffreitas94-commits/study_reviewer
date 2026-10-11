"""Testes de integração para os endpoints REST de autenticação.

Governança multi-tenancy (Sprint 02).
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
from src.application.dto.auth_dto import GoogleUserInfoDTO
from src.application.ports.auth import IGoogleAuthClient, ISessionTokenService
from src.domain.entities import Flashcard, Subject, Topic, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import (
    get_google_client,
    get_session_service,
)
from src.infrastructure.web.app import app


class MockGoogleApiClient(IGoogleAuthClient):
    """Cliente Google OIDC simulado para endpoints REST."""

    def __init__(self) -> None:
        self.code_users: dict[str, GoogleUserInfoDTO] = {}
        self.id_token_users: dict[str, GoogleUserInfoDTO] = {}

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}&redirect_uri={redirect_uri}"

    def exchange_code_for_user_info(self, code: str, redirect_uri: str) -> GoogleUserInfoDTO:
        if code in self.code_users:
            return self.code_users[code]
        raise ValueError("Invalid auth code")

    def verify_id_token(self, id_token: str) -> GoogleUserInfoDTO:
        if id_token in self.id_token_users:
            return self.id_token_users[id_token]
        raise ValueError("Invalid id token")


@pytest.fixture
def api_test_db() -> Generator[sessionmaker[Session]]:
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
def mock_google_api() -> MockGoogleApiClient:
    return MockGoogleApiClient()


@pytest.fixture
def rest_client(
    api_test_db: sessionmaker[Session], mock_google_api: MockGoogleApiClient
) -> Generator[TestClient]:
    """TestClient REST limpo sem overrides forçados de get_current_user."""

    def override_get_db() -> Generator[Session]:
        session = api_test_db()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_google_client] = lambda: mock_google_api

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.integration
def test_api_auth_google_via_code_success(
    rest_client: TestClient,
    mock_google_api: MockGoogleApiClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Valida login e emissão de token via authorization code do Google na API."""
    mock_google_api.code_users["mobile-code-123"] = GoogleUserInfoDTO(
        sub="sub-mobile-001",
        email="mobile@app.com",
        name="Usuário Mobile",
        avatar_url="https://avatar.com/m.png",
    )

    response = rest_client.post(
        "/api/v1/auth/google",
        json={"code": "mobile-code-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "mobile@app.com"
    assert data["user"]["name"] == "Usuário Mobile"

    # Confirma persistência
    with api_test_db() as db:
        user = SqlAlchemyUserRepository(db).get_by_google_sub("sub-mobile-001")
        assert user is not None
        assert user.email == "mobile@app.com"


@pytest.mark.integration
def test_api_auth_google_via_id_token_success(
    rest_client: TestClient,
    mock_google_api: MockGoogleApiClient,
) -> None:
    """Valida autenticação direta via id_token para consumo Flutter/Mobile."""
    mock_google_api.id_token_users["jwt-id-token-xyz"] = GoogleUserInfoDTO(
        sub="sub-flutter-002",
        email="flutter@device.com",
        name="Flutter User",
    )

    response = rest_client.post(
        "/api/v1/auth/google",
        json={"id_token": "jwt-id-token-xyz"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "flutter@device.com"


@pytest.mark.integration
def test_api_auth_google_missing_credentials_returns_400(rest_client: TestClient) -> None:
    """Garante que requisição sem code nem id_token retorne 400 Bad Request."""
    response = rest_client.post(
        "/api/v1/auth/google",
        json={},
    )
    assert response.status_code == 400
    assert "obrigatório" in response.json()["detail"].lower()


@pytest.mark.integration
def test_api_auth_google_invalid_credentials_returns_401(rest_client: TestClient) -> None:
    """Garante que credencial rejeitada pelo Google resulte em 401 Unauthorized."""
    response = rest_client.post(
        "/api/v1/auth/google",
        json={"code": "non-existent-code"},
    )
    assert response.status_code == 401
    assert "falha na autenticação" in response.json()["detail"].lower()


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
    user = User(google_sub="sub-me-01", email="me@test.com", name="Meu Perfil")
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
    # 1. Sem cabeçalho Authorization
    res_none = rest_client.get("/api/v1/auth/me")
    assert res_none.status_code == 401
    assert res_none.headers.get("www-authenticate") == "Bearer"

    # 2. Token adulterado / inválido
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
    owner = User(google_sub="sub-own-api", email="owner.api@test.com", name="Owner API")
    intruder = User(google_sub="sub-int-api", email="intruder.api@test.com", name="Intruder API")

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

    # 1. Intruder tenta alternar: 403 Forbidden
    res_forbidden = rest_client.post(
        f"/api/v1/subjects/{subject_id}/toggle-public",
        json={"is_public": True},
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert res_forbidden.status_code == 403

    # 2. Dono alterna: 200 OK
    res_success = rest_client.post(
        f"/api/v1/subjects/{subject_id}/toggle-public",
        json={"is_public": True},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_success.status_code == 200
    assert res_success.json()["is_public"] is True

    # 3. Matéria inexistente: 404 Not Found
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
    user_a = User(google_sub="sub-a", email="a@test.com", name="Estudante A")
    user_b = User(google_sub="sub-b", email="b@test.com", name="Estudante B")

    with api_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(user_a)
        user_repo.save(user_b)

        subject_repo = SqlAlchemySubjectRepository(db)
        topic_repo = SqlAlchemyTopicRepository(db)
        card_repo = SqlAlchemyFlashcardRepository(db)

        # Matéria privada de A com 1 tema e 1 card
        priv_a = Subject(name="Matéria Privada de A", owner_id=user_a.id, is_public=False)
        subject_repo.save(priv_a)
        top_priv_a = Topic(subject_id=priv_a.id, name="Tema Privado")
        topic_repo.save(top_priv_a)
        card_priv_a = Flashcard(
            topic_id=top_priv_a.id, front="Segredo A", back="Resposta A", position=100
        )
        card_repo.save(card_priv_a)

        # Matéria pública de A com 1 tema e 1 card
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

    # Regra 1: User B não pode listar temas da matéria privada de A (403 Forbidden)
    res_list_topics = rest_client.get(f"/api/v1/subjects/{priv_a.id}/topics", headers=headers_b)
    assert res_list_topics.status_code == 403

    # Regra 2: User B não pode estudar a matéria privada de A (403 Forbidden)
    res_study_priv = rest_client.get(
        f"/api/v1/study/next?subject_id={priv_a.id}", headers=headers_b
    )
    assert res_study_priv.status_code == 403

    res_batch_priv = rest_client.get(
        f"/api/v1/study/batch?subject_id={priv_a.id}", headers=headers_b
    )
    assert res_batch_priv.status_code == 403

    # Regra 3: User B não pode criar tópico na matéria de A (mesmo na pública) (403 Forbidden)
    res_create_topic = rest_client.post(
        "/api/v1/topics",
        json={"subject_id": str(pub_a.id), "name": "Novo Tema por B"},
        headers=headers_b,
    )
    assert res_create_topic.status_code == 403

    # Regra 4: User B não pode criar flashcard na matéria de A (403 Forbidden)
    res_create_card = rest_client.post(
        "/api/v1/flashcards",
        json={"topic_id": str(top_pub_a.id), "front": "Card B", "back": "Resp B"},
        headers=headers_b,
    )
    assert res_create_card.status_code == 403

    # Regra 5: User B PODE listar temas da matéria pública de A (200 OK)
    res_pub_topics = rest_client.get(f"/api/v1/subjects/{pub_a.id}/topics", headers=headers_b)
    assert res_pub_topics.status_code == 200
    assert len(res_pub_topics.json()) == 1

    # Regra 6: User B PODE estudar a matéria pública de A com sua própria sessão isolada (200 OK)
    res_study_pub = rest_client.get(f"/api/v1/study/next?subject_id={pub_a.id}", headers=headers_b)
    assert res_study_pub.status_code == 200
    assert res_study_pub.json()["front"] == "Card Público"


@pytest.mark.security
def test_api_auth_google_user_not_found_after_provisioning(
    rest_client: TestClient,
    mock_google_api: MockGoogleApiClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida erro 401 caso usuário não seja encontrado após provisionamento.

    Vulnerabilidade prevenida: Inconsistência de estado de identidade pós-autenticação.
    Garantia de segurança: Retorna 401 se get_by_id falhar em recuperar a entidade persistida.
    """
    mock_google_api.code_users["test-code-ghost"] = GoogleUserInfoDTO(
        sub="sub-ghost",
        email="ghost@test.com",
        name="Ghost",
    )
    monkeypatch.setattr(SqlAlchemyUserRepository, "get_by_id", lambda self, uid: None)

    response = rest_client.post(
        "/api/v1/auth/google",
        json={"code": "test-code-ghost"},
    )
    assert response.status_code == 401
    assert "Usuário não encontrado após provisionamento" in response.json()["detail"]


@pytest.mark.integration
def test_api_get_topics_subject_not_found(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Retorna 404 ao tentar listar tópicos de uma matéria inexistente."""
    user = User(google_sub="sub-owner-notfound", email="nf@test.com", name="NF User")
    with api_test_db() as db:
        SqlAlchemyUserRepository(db).save(user)

    session_service = get_session_service()
    token = session_service.create_session_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    res = rest_client.get(f"/api/v1/subjects/{uuid4()}/topics", headers=headers)
    assert res.status_code == 404
    assert "Matéria não encontrada" in res.json()["detail"]
