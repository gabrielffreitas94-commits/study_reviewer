"""Testes de integração para autenticação Web local e demo.

Cookies de sessão HttpOnly/SameSite=Lax e proteção contra Open Redirect (CWE-601).
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
from src.application.ports.auth import ISessionTokenService
from src.domain.entities import Subject, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_session_service
from src.infrastructure.web.app import app


@pytest.fixture
def test_db_session() -> Generator[sessionmaker[Session], None, None]:
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
def auth_client(
    test_db_session: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    """TestClient sem usuário autenticado por padrão (para testar fluxo de login local)."""

    def override_get_db() -> Generator[Session, None, None]:
        session = test_db_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_login_page_renders_local_forms_and_no_google_oauth(auth_client: TestClient) -> None:
    """Verifica se /auth/login renderiza login local, cadastro e acesso demo sem Google OAuth."""
    response = auth_client.get("/auth/login")
    assert response.status_code == 200
    html = response.text

    assert 'action="/auth/login"' in html
    assert 'action="/auth/register"' in html
    assert 'action="/auth/demo"' in html
    assert "Entrar como Estudante Demo (Offline)" in html

    assert "/auth/google" not in html
    assert "Continuar com o Google" not in html


@pytest.mark.integration
def test_login_page_redirects_if_already_authenticated(
    auth_client: TestClient, test_db_session: sessionmaker[Session]
) -> None:
    """Garante que usuário com sessão ativa seja redirecionado ao acessar /auth/login."""
    user = User(google_sub="local:active@test.com", email="active@test.com", name="User Ativo")
    with test_db_session() as db:
        SqlAlchemyUserRepository(db).save(user)

    session_service: ISessionTokenService = get_session_service()
    token = session_service.create_session_token(user.id, user.email)

    auth_client.cookies.set("session_token", token)
    response = auth_client.get("/auth/login?next=/study", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/study"


@pytest.mark.security
def test_web_register_sets_httponly_samesite_cookie_and_redirects(
    auth_client: TestClient, test_db_session: sessionmaker[Session]
) -> None:
    """Valida criação de conta via POST /auth/register com cookie HttpOnly e SameSite=Lax.

    Vulnerabilidade prevenida: Roubo de token de sessão via XSS (document.cookie) e CSRF.
    Garantia de segurança: O cookie session_token é emitido criptografado com flags HttpOnly
    e SameSite=Lax, e redireciona apenas para destinos locais seguros.
    """
    response = auth_client.post(
        "/auth/register",
        data={
            "name": "Estudante Local",
            "email": "estudante.local@test.com",
            "password": "SenhaSegura123!",
            "next": "/questions/study",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/questions/study"
    assert "session_token" in response.cookies

    set_cookie_headers = response.headers.get_list("set-cookie")
    session_cookies = [h for h in set_cookie_headers if h.startswith("session_token=")]
    assert len(session_cookies) == 1
    cookie_header_lower = session_cookies[0].lower()
    assert "httponly" in cookie_header_lower
    assert "samesite=lax" in cookie_header_lower

    with test_db_session() as db:
        user = SqlAlchemyUserRepository(db).get_by_email("estudante.local@test.com")
        assert user is not None
        assert user.name == "Estudante Local"


@pytest.mark.integration
def test_web_register_error_redirects_to_login_with_error(auth_client: TestClient) -> None:
    """Garante redirecionamento para /auth/login?error=... em falha de cadastro local."""
    res_bad_pw = auth_client.post(
        "/auth/register",
        data={
            "name": "Curto",
            "email": "curto@test.com",
            "password": "123",
            "next": "/study-maps",
        },
        follow_redirects=False,
    )
    assert res_bad_pw.status_code == 303
    assert res_bad_pw.headers["location"].startswith("/auth/login?error=")


@pytest.mark.security
def test_web_login_valid_and_invalid_credentials_with_cookie_flags(
    auth_client: TestClient,
) -> None:
    """Valida login local via POST /auth/login e resposta uniforme em caso de erro.

    Vulnerabilidade prevenida: Sequestro de sessão via XSS e enumeração de contas no login Web.
    Garantia de segurança: Credenciais válidas emitem cookie HttpOnly/SameSite=Lax; falhas
    redirecionam para /auth/login?error=... com mensagem genérica uniforme.
    """
    auth_client.post(
        "/auth/register",
        data={
            "name": "Login Web",
            "email": "web.login@test.com",
            "password": "Password123!",
        },
        follow_redirects=False,
    )
    auth_client.cookies.clear()

    # 1. Login válido
    ok_res = auth_client.post(
        "/auth/login",
        data={
            "email": "web.login@test.com",
            "password": "Password123!",
            "next": "/performance",
        },
        follow_redirects=False,
    )
    assert ok_res.status_code == 303
    assert ok_res.headers["location"] == "/performance"
    assert "session_token" in ok_res.cookies

    set_cookie_headers = ok_res.headers.get_list("set-cookie")
    session_cookies = [h for h in set_cookie_headers if h.startswith("session_token=")]
    assert len(session_cookies) == 1
    assert "httponly" in session_cookies[0].lower()
    assert "samesite=lax" in session_cookies[0].lower()

    # 2. Senha inválida e e-mail inexistente retornam erro idêntico
    auth_client.cookies.clear()
    bad_pw = auth_client.post(
        "/auth/login",
        data={"email": "web.login@test.com", "password": "WrongPassword!"},
        follow_redirects=False,
    )
    bad_email = auth_client.post(
        "/auth/login",
        data={"email": "naoexiste@test.com", "password": "WrongPassword!"},
        follow_redirects=False,
    )
    assert bad_pw.status_code == 303
    assert bad_email.status_code == 303
    assert bad_pw.headers["location"] == bad_email.headers["location"]
    assert "/auth/login?error=" in bad_pw.headers["location"]


@pytest.mark.security
def test_web_demo_login_sets_secure_cookie_and_is_idempotent(
    auth_client: TestClient, test_db_session: sessionmaker[Session]
) -> None:
    """Valida acesso instantâneo demo via POST /auth/demo com cookie HttpOnly e SameSite=Lax.

    Vulnerabilidade prevenida: Exposição de token de sessão demo a scripts no navegador.
    Garantia de segurança: Emite cookie session_token HttpOnly e SameSite=Lax e reutiliza o
    mesmo usuário demo de forma idempotente.
    """
    res1 = auth_client.post(
        "/auth/demo",
        data={"next": "/study-maps"},
        follow_redirects=False,
    )
    assert res1.status_code == 303
    assert res1.headers["location"] == "/study-maps"
    assert "session_token" in res1.cookies

    set_cookie_headers = res1.headers.get_list("set-cookie")
    session_cookies = [h for h in set_cookie_headers if h.startswith("session_token=")]
    assert len(session_cookies) == 1
    assert "httponly" in session_cookies[0].lower()
    assert "samesite=lax" in session_cookies[0].lower()

    with test_db_session() as db:
        u1 = SqlAlchemyUserRepository(db).get_by_email("demo@studyreviewer.local")
        assert u1 is not None
        first_id = u1.id

    auth_client.cookies.clear()
    res2 = auth_client.post("/auth/demo", follow_redirects=False)
    assert res2.status_code == 303
    assert res2.headers["location"] == "/study-maps"

    with test_db_session() as db:
        u2 = SqlAlchemyUserRepository(db).get_by_email("demo@studyreviewer.local")
        assert u2 is not None
        assert u2.id == first_id


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
    owner = User(google_sub="local:owner@test.com", email="owner@test.com", name="Owner")
    intruder = User(
        google_sub="local:intruder@test.com", email="intruder@test.com", name="Intruder"
    )

    with test_db_session() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(owner)
        user_repo.save(intruder)
        subject_repo = SqlAlchemySubjectRepository(db)
        subject = Subject(name="Direito Civil", owner_id=owner.id, is_public=False)
        subject_repo.save(subject)
        subject_id = subject.id

    session_service: ISessionTokenService = get_session_service()

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
@pytest.mark.security
def test_login_page_and_post_routes_open_redirect_sanitized(
    auth_client: TestClient,
    test_db_session: sessionmaker[Session],
) -> None:
    """Valida neutralização de tentativas de Open Redirect nas rotas GET e POST de autenticação.

    Vulnerabilidade prevenida: Open Redirect (CWE-601) e ataques de phishing através de
    parâmetros de redirecionamento manipulados para domínios externos.
    Garantia de segurança: O sistema sanitiza qualquer URL de destino que não seja estritamente
    relativa no mesmo domínio, revertendo para a rota segura '/study-maps'.
    """
    user = User(google_sub="local:redir@test.com", email="redir@test.com", name="Redir")
    with test_db_session() as db:
        SqlAlchemyUserRepository(db).save(user)

    session_service: ISessionTokenService = get_session_service()
    token = session_service.create_session_token(user.id, user.email)
    auth_client.cookies.set("session_token", token)

    # 1. GET /auth/login com URL externa absoluta
    res1 = auth_client.get("/auth/login?next=https://evil.com/phishing", follow_redirects=False)
    assert res1.status_code == 303
    assert res1.headers["location"] == "/study-maps"

    # 2. GET /auth/login com protocolo relativo (//evil.com)
    res2 = auth_client.get("/auth/login?next=//evil.com", follow_redirects=False)
    assert res2.status_code == 303
    assert res2.headers["location"] == "/study-maps"

    # 3. GET /auth/login com barra invertida (/\evil.com)
    res3 = auth_client.get("/auth/login?next=/\\evil.com", follow_redirects=False)
    assert res3.status_code == 303
    assert res3.headers["location"] == "/study-maps"

    # 4. Rota relativa legítima é aceita
    res4 = auth_client.get("/auth/login?next=/subjects", follow_redirects=False)
    assert res4.status_code == 303
    assert res4.headers["location"] == "/subjects"

    # 5. Parâmetro next vazio cai no fallback seguro default
    res5 = auth_client.get("/auth/login?next=", follow_redirects=False)
    assert res5.status_code == 303
    assert res5.headers["location"] == "/study-maps"

    # 6. POST /auth/register, POST /auth/login e POST /auth/demo também bloqueiam Open Redirect
    auth_client.cookies.clear()
    reg_evil = auth_client.post(
        "/auth/register",
        data={
            "name": "Evil Next",
            "email": "evilnext@test.com",
            "password": "Password123!",
            "next": "https://evil.com",
        },
        follow_redirects=False,
    )
    assert reg_evil.status_code == 303
    assert reg_evil.headers["location"] == "/study-maps"

    auth_client.cookies.clear()
    login_evil = auth_client.post(
        "/auth/login",
        data={
            "email": "evilnext@test.com",
            "password": "Password123!",
            "next": "//evil.com",
        },
        follow_redirects=False,
    )
    assert login_evil.status_code == 303
    assert login_evil.headers["location"] == "/study-maps"

    auth_client.cookies.clear()
    demo_evil = auth_client.post(
        "/auth/demo",
        data={"next": "/\\evil.com"},
        follow_redirects=False,
    )
    assert demo_evil.status_code == 303
    assert demo_evil.headers["location"] == "/study-maps"


@pytest.mark.integration
def test_get_current_user_preserves_query_string(
    auth_client: TestClient,
) -> None:
    """Valida que o redirecionamento para login preserva parâmetros de query string."""
    res = auth_client.get("/study?subject_id=123&mode=review", follow_redirects=False)
    assert res.status_code == 303
    expected_next = urllib.parse.quote("/study?subject_id=123&mode=review", safe="")
    assert res.headers["location"] == f"/auth/login?next={expected_next}"


@pytest.mark.integration
def test_auth_privacy_routes_redirect(auth_client: TestClient) -> None:
    """Valida que /auth/privacy e /auth/account-deletion-request redirecionam para rotas canônicas."""
    res_privacy = auth_client.get("/auth/privacy", follow_redirects=False)
    assert res_privacy.status_code == 301
    assert res_privacy.headers["location"] == "/privacy"

    res_del = auth_client.get("/auth/account-deletion-request", follow_redirects=False)
    assert res_del.status_code == 301
    assert res_del.headers["location"] == "/privacy/account-deletion-request"
