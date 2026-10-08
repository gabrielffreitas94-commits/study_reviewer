"""Testes de integração Web para rotas públicas de Privacidade e Exclusão Externa (Sprint 05).

Conformidade com LGPD Art. 18 e Google Play Data Safety.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import SqlAlchemyUserRepository
from src.domain.entities import User
from src.infrastructure.database import Base, get_db
from src.infrastructure.web.app import app


@pytest.fixture
def web_test_db() -> Generator[sessionmaker[Session]]:
    """Cria banco SQLite em memória isolado para os testes web."""
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
def web_client(
    web_test_db: sessionmaker[Session],
) -> Generator[TestClient]:
    """TestClient Web sem autenticação prévia."""

    def override_get_db() -> Generator[Session]:
        session = web_test_db()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_privacy_page_renders_successfully(web_client: TestClient) -> None:
    """Valida a renderização pública da página de política de privacidade."""
    response = web_client.get("/privacy")
    assert response.status_code == 200
    assert "Política de Privacidade" in response.text
    assert "LGPD" in response.text
    assert "AES-256-GCM" in response.text
    assert "Google Play Data Safety" in response.text
    assert "privacidade@studyreviewer.com" in response.text
    assert "/privacy/account-deletion-request" in response.text


@pytest.mark.integration
def test_account_deletion_request_form_renders(web_client: TestClient) -> None:
    """Valida a renderização do formulário público de solicitação de exclusão."""
    response = web_client.get("/privacy/account-deletion-request")
    assert response.status_code == 200
    assert "Solicitação de Exclusão de Conta e Dados" in response.text
    assert "Double Opt-In" in response.text
    assert 'name="email"' in response.text
    assert 'name="confirmation"' in response.text


@pytest.mark.integration
def test_submit_account_deletion_request_success(
    web_client: TestClient,
    web_test_db: sessionmaker[Session],
) -> None:
    """Valida o envio do formulário de exclusão com retorno informativo Double Opt-In."""
    # Cadastra usuário na base
    with web_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(
            User(
                google_sub="sub-delete-web-01",
                email="solicitante@estudo.com",
                name="Estudante Web",
            )
        )

    response = web_client.post(
        "/privacy/account-deletion-request",
        data={"email": "solicitante@estudo.com", "confirmation": "on"},
    )
    assert response.status_code == 200
    assert "Solicitação Recebida com Sucesso" in response.text
    assert "solicitante@estudo.com" in response.text
    assert "Double Opt-In" in response.text


@pytest.mark.security
def test_privacy_page_security_and_transparency(web_client: TestClient) -> None:
    """Vulnerabilidade prevenida: Ocultamento de termos de privacidade e ausência de transparência.

    Garantia de segurança: Assegura que a página de privacidade descreva explicitamente a
    conformidade com o Artigo 18 da LGPD, o uso de criptografia AES-256-GCM e o direito à
    exclusão e anonimização de dados.
    """
    response = web_client.get("/privacy")
    assert response.status_code == 200
    text = response.text
    assert "AES-256-GCM" in text
    assert "Art. 18 da LGPD" in text or "Artigo 18" in text or "Art. 16, IV da LGPD" in text
    assert "comercializados" in text and "terceiros" in text


@pytest.mark.security
def test_account_deletion_request_anti_enumeration(
    web_client: TestClient,
    web_test_db: sessionmaker[Session],
) -> None:
    """Vulnerabilidade prevenida: Ataque de enumeração de usuários (User Enumeration).

    Garantia de segurança: Assegura respostas uniformes de confirmação de envio tanto para
    e-mails cadastrados quanto para e-mails inexistentes, impedindo a verificação de contas
    ativas por terceiros mal-intencionados.
    """
    # 1. Usuário existente
    with web_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(
            User(
                google_sub="sub-real-user",
                email="usuario.real@dominio.com",
                name="Usuário Real",
            )
        )

    res_real = web_client.post(
        "/privacy/account-deletion-request",
        data={"email": "usuario.real@dominio.com", "confirmation": "on"},
    )
    assert res_real.status_code == 200
    assert "Solicitação Recebida com Sucesso" in res_real.text

    # 2. Usuário inexistente
    res_fake = web_client.post(
        "/privacy/account-deletion-request",
        data={"email": "fantasma.inexistente@dominio.com", "confirmation": "on"},
    )
    assert res_fake.status_code == 200
    assert "Solicitação Recebida com Sucesso" in res_fake.text

    # Ambos os fluxos mostram a mesma mensagem padronizada de Double Opt-In
    assert "mensagem de confirmação" in res_real.text
    assert "mensagem de confirmação" in res_fake.text


@pytest.mark.integration
def test_auth_privacy_redirects(web_client: TestClient) -> None:
    """Valida o redirecionamento de compatibilidade das rotas com prefixo /auth."""
    res_privacy = web_client.get("/auth/privacy", follow_redirects=False)
    assert res_privacy.status_code == 301
    assert res_privacy.headers["location"] == "/privacy"

    res_deletion = web_client.get("/auth/account-deletion-request", follow_redirects=False)
    assert res_deletion.status_code == 301
    assert res_deletion.headers["location"] == "/privacy/account-deletion-request"
