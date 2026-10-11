"""Testes de integração para a exclusão de conta e logout formal via API REST (Sprint 05).

Conformidade com LGPD (Art. 18 / Art. 16, IV) e Google Play Data Safety.
"""

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
def rest_client(
    api_test_db: sessionmaker[Session],
) -> Generator[TestClient]:
    """TestClient REST limpo com isolamento de banco."""

    def override_get_db() -> Generator[Session]:
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
def test_delete_account_api_success(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Valida a exclusão de conta via endpoint DELETE /api/v1/auth/account."""
    user = User(
        google_sub="sub-delete-api-01",
        email="delete.api@estudo.com",
        name="Usuário Para Deletar",
    )
    with api_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(user)
        subject_repo = SqlAlchemySubjectRepository(db)
        subject = Subject(name="Matéria a ser removida", owner_id=user.id, is_public=False)
        subject_repo.save(subject)
        subject_id = subject.id

    session_service: ISessionTokenService = get_session_service()
    token = session_service.create_session_token(user.id, user.email)

    response = rest_client.delete(
        "/api/v1/auth/account",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Conta e dados pessoais excluídos com sucesso."}

    # Valida que o usuário e suas matérias foram removidos da base
    with api_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        assert user_repo.get_by_id(user.id) is None
        subject_repo = SqlAlchemySubjectRepository(db)
        assert subject_repo.get_by_id(subject_id) is None


@pytest.mark.security
def test_delete_account_anti_idor_and_identity_isolation(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Vulnerabilidade prevenida: Impede IDOR e exclusão indevida de contas alheias.

    Garantia de segurança: Assegura que o endpoint extraia a identidade do usuário exclusivamente
    do Bearer Token criptografado validado por get_current_user, sem aceitar IDs arbitrários no
    payload ou query.
    """
    user_victim = User(
        google_sub="sub-victim-01",
        email="vitima@estudo.com",
        name="Usuário Vítima",
    )
    user_attacker = User(
        google_sub="sub-attacker-01",
        email="atacante@estudo.com",
        name="Usuário Atacante",
    )
    with api_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(user_victim)
        user_repo.save(user_attacker)

    session_service: ISessionTokenService = get_session_service()
    attacker_token = session_service.create_session_token(user_attacker.id, user_attacker.email)

    # Atacante tenta passar parâmetros maliciosos tentando forçar a exclusão da vítima
    response = rest_client.delete(
        f"/api/v1/auth/account?user_id={user_victim.id}",
        headers={"Authorization": f"Bearer {attacker_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Conta e dados pessoais excluídos com sucesso."}

    # Garante que a vítima permaneceu absolutamente intacta
    with api_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        assert user_repo.get_by_id(user_victim.id) is not None
        # E que o atacante é quem teve a própria conta excluída
        assert user_repo.get_by_id(user_attacker.id) is None


@pytest.mark.security
def test_delete_account_unauthenticated_rejected(
    rest_client: TestClient,
) -> None:
    """Vulnerabilidade prevenida: Acesso anônimo ou não autorizado ao endpoint de exclusão de conta.

    Garantia de segurança: Rejeita qualquer requisição sem token Bearer válido com status HTTP 401
    Unauthorized e cabeçalho de autenticação.
    """
    # 1. Sem token
    res_no_token = rest_client.delete("/api/v1/auth/account")
    assert res_no_token.status_code == 401
    assert res_no_token.headers.get("www-authenticate") == "Bearer"

    # 2. Token inválido/corrompido
    res_bad_token = rest_client.delete(
        "/api/v1/auth/account",
        headers={"Authorization": "Bearer token-falso-adulterado"},
    )
    assert res_bad_token.status_code == 401


@pytest.mark.integration
def test_logout_api_success(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
) -> None:
    """Valida o logout formal via endpoint POST /api/v1/auth/logout."""
    user = User(
        google_sub="sub-logout-api-01",
        email="logout.api@estudo.com",
        name="Usuário Logout",
    )
    with api_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(user)

    session_service: ISessionTokenService = get_session_service()
    token = session_service.create_session_token(user.id, user.email)

    response = rest_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Logout efetuado com sucesso."}


@pytest.mark.security
def test_logout_api_unauthenticated_rejected(
    rest_client: TestClient,
) -> None:
    """Vulnerabilidade prevenida: Execução não autenticada da operação formal de encerramento.

    Garantia de segurança: Rejeita chamadas anônimas ao endpoint de logout com status HTTP 401
    Unauthorized e cabeçalho WWW-Authenticate: Bearer.
    """
    response = rest_client.post("/api/v1/auth/logout")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.integration
def test_delete_account_api_entity_not_found(
    rest_client: TestClient,
    api_test_db: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida retorno HTTP 404 caso o use case levante EntityNotFoundError."""
    user = User(
        google_sub="sub-delete-api-404",
        email="delete.404@estudo.com",
        name="Usuário 404",
    )
    with api_test_db() as db:
        user_repo = SqlAlchemyUserRepository(db)
        user_repo.save(user)

    session_service: ISessionTokenService = get_session_service()
    token = session_service.create_session_token(user.id, user.email)

    from src.application.use_cases.auth_use_cases import DeleteAccountUseCase
    from src.domain.exceptions import EntityNotFoundError

    def mock_execute(self: DeleteAccountUseCase, user_id: object) -> None:
        raise EntityNotFoundError("Usuário inexistente para exclusão.")

    monkeypatch.setattr(DeleteAccountUseCase, "execute", mock_execute)

    response = rest_client.delete(
        "/api/v1/auth/account",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Usuário inexistente para exclusão."
