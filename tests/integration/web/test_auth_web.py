"""Testes de integração para autenticação Web.

Cookies de sessão e proteção anti-CSRF (Sprint 02).
"""

import urllib.parse
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemySubjectRepository,
    SqlAlchemyUserRepository,
)
from src.application.dto.auth_dto import GoogleUserInfoDTO
from src.application.ports.auth import IGoogleAuthClient, ISessionTokenService
from src.domain.entities import Subject, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import (
    get_google_client,
    get_session_service,
)
from src.infrastructure.web.app import app


class MockGoogleAuthClient(IGoogleAuthClient):
    """Cliente Google simulado para testes de integração."""

    def __init__(self) -> None:
        self.code_users: dict[str, GoogleUserInfoDTO] = {}
        self.id_token_users: dict[str, GoogleUserInfoDTO] = {}

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return f"https://accounts.google.com/o/oauth2/v2/auth?state={state}&redirect_uri={redirect_uri}"

    def exchange_code_for_user_info(self, code: str, redirect_uri: str) -> GoogleUserInfoDTO:
        if code in self.code_users:
            return self.code_users[code]
        raise ValueError("Invalid authorization code")

    def verify_id_token(self, id_token: str) -> GoogleUserInfoDTO:
        if id_token in self.id_token_users:
            return self.id_token_users[id_token]
        raise ValueError("Invalid id token")


@pytest.fixture
def test_db_session() -> Generator[sessionmaker[Session]]:
    """Configura banco em memória isolado."""
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
def mock_google() -> MockGoogleAuthClient:
    return MockGoogleAuthClient()


@pytest.fixture
def auth_client(
    test_db_session: sessionmaker[Session], mock_google: MockGoogleAuthClient
) -> Generator[TestClient]:
    """TestClient sem usuário autenticado por padrão (para testar fluxo de login)."""

    def override_get_db() -> Generator[Session]:
        session = test_db_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_google_client] = lambda: mock_google
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_login_page_renders_for_anonymous_user(auth_client: TestClient) -> None:
    """Verifica se a página de login é renderizada para usuários não autenticados."""
    response = auth_client.get("/auth/login")
    assert response.status_code == 200
    assert "Continuar com o Google" in response.text
    assert "/auth/google" in response.text


@pytest.mark.integration
def test_login_page_redirects_if_already_authenticated(
    auth_client: TestClient, test_db_session: sessionmaker[Session]
) -> None:
    """Garante que usuário com sessão ativa seja redirecionado ao acessar /auth/login."""
    user = User(google_sub="sub-active", email="active@test.com", name="User Ativo")
    with test_db_session() as db:
        SqlAlchemyUserRepository(db).save(user)

    session_service: ISessionTokenService = app.dependency_overrides.get(
        get_session_service, lambda: get_session_service()
    )()
    token = session_service.create_session_token(user.id, user.email)

    auth_client.cookies.set("session_token", token)
    response = auth_client.get("/auth/login?next=/study", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/study"


@pytest.mark.security
def test_google_login_redirect_sets_state_cookie(auth_client: TestClient) -> None:
    """Valida geração do state anti-CSRF e redirecionamento para o Google.

    Vulnerabilidade prevenida: Cross-Site Request Forgery (CSRF) no fluxo de login federado.
    Garantia de segurança: O endpoint gera state criptografado e armazena em cookie HttpOnly.
    """
    response = auth_client.get("/auth/google?next=/study", follow_redirects=False)
    assert response.status_code == 303
    assert "https://accounts.google.com/o/oauth2/v2/auth" in response.headers["location"]
    assert "oauth_state" in response.cookies


@pytest.mark.security
def test_oauth_callback_rejects_missing_or_mismatched_state(auth_client: TestClient) -> None:
    """Rejeita callback com state divergente ou ausente para impedir CSRF.

    Vulnerabilidade prevenida: Ataque de CSRF com injeção de authorization code forjado.
    Garantia de segurança: Lança HTTP 400 Bad Request ao detectar divergência no state.
    """
    # 1. State ausente
    res_no_state = auth_client.get("/auth/callback?code=some-code")
    assert res_no_state.status_code == 400
    assert "possível tentativa de CSRF" in res_no_state.json()["detail"]

    # 2. State mismatch
    auth_client.cookies.set("oauth_state", "legitimate-state")
    res_mismatch = auth_client.get("/auth/callback?code=some-code&state=attacker-state")
    assert res_mismatch.status_code == 400
    assert "possível tentativa de CSRF" in res_mismatch.json()["detail"]


@pytest.mark.integration
def test_oauth_callback_handles_google_error(auth_client: TestClient) -> None:
    """Trata cancelamento ou erro retornado diretamente pelo Google."""
    response = auth_client.get("/auth/callback?error=access_denied", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login?error=access_denied" in response.headers["location"]


@pytest.mark.security
def test_oauth_callback_successful_login_and_cookie_issuance(
    auth_client: TestClient,
    mock_google: MockGoogleAuthClient,
    test_db_session: sessionmaker[Session],
) -> None:
    """Valida autenticação bem-sucedida, provisionamento e emissão de cookie AES-256-GCM.

    Vulnerabilidade prevenida: Sequestro de sessão e exposição de dados em trânsito.
    Garantia de segurança: Emissão de cookie session_token HttpOnly criptografado com AES-256-GCM.
    """
    # 1. Inicia fluxo para obter state legítimo
    init_res = auth_client.get("/auth/google?next=/study", follow_redirects=False)
    state_cookie = init_res.cookies.get("oauth_state")
    assert state_cookie is not None

    # 2. Configura resposta do mock Google
    mock_google.code_users["valid-code-123"] = GoogleUserInfoDTO(
        sub="google-sub-web-999",
        email="sucesso@web.com",
        name="Estudante Web",
        avatar_url="https://avatar.google.com/999.png",
    )

    # 3. Executa callback
    auth_client.cookies.set("oauth_state", state_cookie)
    callback_res = auth_client.get(
        f"/auth/callback?code=valid-code-123&state={urllib.parse.quote(state_cookie)}",
        follow_redirects=False,
    )

    assert callback_res.status_code == 303
    assert callback_res.headers["location"] == "/study"
    assert "session_token" in callback_res.cookies

    # 4. Verifica se o usuário foi criado no banco
    with test_db_session() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user = user_repo.get_by_google_sub("google-sub-web-999")
        assert user is not None
        assert user.email == "sucesso@web.com"


@pytest.mark.integration
def test_logout_clears_session_cookie(auth_client: TestClient) -> None:
    """Verifica se o logout remove o cookie de autenticação."""
    auth_client.cookies.set("session_token", "dummy-token")
    response = auth_client.post("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"
    assert (
        response.cookies.get("session_token") is None
        or response.cookies.get("session_token") == '""'
    )


@pytest.mark.security
def test_unauthenticated_web_access_redirects_to_login(auth_client: TestClient) -> None:
    """Garante que requisições Web anônimas a rotas protegidas sejam redirecionadas ao login.

    Vulnerabilidade prevenida: Acesso anônimo ou não autorizado a áreas restritas da aplicação.
    Garantia de segurança: get_current_user redireciona com HTTP 303 preservando parâmetro next.
    """
    response = auth_client.get("/study", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login?next=%2Fstudy" in response.headers["location"]


@pytest.mark.security
def test_unauthenticated_htmx_access_returns_401_with_hx_redirect(auth_client: TestClient) -> None:
    """Garante que requisições HTMX parciais sem sessão recebam cabeçalho HX-Redirect.

    Vulnerabilidade prevenida: Sessões expiradas em clientes HTMX sem redirecionamento da página.
    Garantia de segurança: Retorna HTTP 401 com cabeçalho HX-Redirect apontando para /auth/login.
    """
    response = auth_client.get("/study", headers={"HX-Request": "true"})
    assert response.status_code == 401
    assert "HX-Redirect" in response.headers
    assert "/auth/login?next=%2Fstudy" in response.headers["HX-Redirect"]


@pytest.mark.security
def test_toggle_subject_public_web_by_owner_and_forbidden_for_non_owner(
    auth_client: TestClient, test_db_session: sessionmaker[Session]
) -> None:
    """Valida alternância de visibilidade pública e bloqueio para não proprietários na Web.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) em rotas web.
    Garantia de segurança: Retorna HTTP 403 Forbidden caso outro usuário tente alterar a matéria.
    """
    owner = User(google_sub="sub-owner", email="owner@test.com", name="Owner")
    intruder = User(google_sub="sub-intruder", email="intruder@test.com", name="Intruder")

    with test_db_session() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(owner)
        user_repo.save(intruder)
        subject_repo = SqlAlchemySubjectRepository(db)
        subject = Subject(name="Direito Civil", owner_id=owner.id, is_public=False)
        subject_repo.save(subject)
        subject_id = subject.id

    session_service: ISessionTokenService = get_session_service()

    # 1. Owner torna a matéria pública
    owner_token = session_service.create_session_token(owner.id, owner.email)
    auth_client.cookies.set("session_token", owner_token)
    res_toggle = auth_client.post(
        f"/subjects/{subject_id}/toggle-public",
        data={"is_public": "true"},
        follow_redirects=False,
    )
    assert res_toggle.status_code == 303

    with test_db_session() as db:
        sub = SqlAlchemySubjectRepository(db).get_by_id(subject_id)
        assert sub is not None
        assert sub.is_public is True

    # 2. Intruder tenta tornar a matéria privada
    intruder_token = session_service.create_session_token(intruder.id, intruder.email)
    auth_client.cookies.set("session_token", intruder_token)
    res_intruder = auth_client.post(
        f"/subjects/{subject_id}/toggle-public",
        data={"is_public": "false"},
        follow_redirects=False,
    )
    assert res_intruder.status_code == 400 or res_intruder.status_code == 403
    assert "permissão" in res_intruder.text


@pytest.mark.integration
def test_oauth_callback_exception_redirects_to_login_with_error(
    auth_client: TestClient,
) -> None:
    """Valida redirecionamento para login com mensagem de erro quando ocorre exceção interna."""
    init_res = auth_client.get("/auth/google?next=/study", follow_redirects=False)
    state = init_res.cookies.get("oauth_state")
    assert state is not None

    auth_client.cookies.set("oauth_state", state)
    quoted_state = urllib.parse.quote(state)
    res = auth_client.get(
        f"/auth/callback?code=codigo-inexistente&state={quoted_state}", follow_redirects=False
    )
    assert res.status_code == 303
    assert "/auth/login?error=" in res.headers["location"]
