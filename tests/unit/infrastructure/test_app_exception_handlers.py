"""Testes unitários para os manipuladores de exceções da aplicação FastAPI (Sprint 02)."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.domain.exceptions import ResourceOwnershipError, UnauthorizedError
from src.infrastructure.web.app import create_app


@pytest.fixture
def app_with_test_routes() -> Generator[TestClient]:
    app = create_app()

    @app.get("/api/test-ownership-error")
    def api_ownership() -> None:
        raise ResourceOwnershipError("Acesso proibido pela regra de posse")

    @app.get("/web/test-ownership-error")
    def web_ownership() -> None:
        raise ResourceOwnershipError("Acesso proibido pela regra de posse")

    @app.get("/api/test-unauthorized-error")
    def api_unauthorized() -> None:
        raise UnauthorizedError("Token expirado ou ausente")

    @app.get("/web/test-unauthorized-error")
    def web_unauthorized() -> None:
        raise UnauthorizedError("Token expirado ou ausente")

    with TestClient(app) as client:
        yield client


@pytest.mark.unit
def test_resource_ownership_handler(app_with_test_routes: TestClient) -> None:
    """Verifica respostas JSON (403) e HTML (403) do handler de ResourceOwnershipError."""
    # 1. API: JSON 403
    res_api = app_with_test_routes.get("/api/test-ownership-error")
    assert res_api.status_code == 403
    assert res_api.json()["detail"] == "Acesso proibido pela regra de posse"

    # 2. Web: HTML 403
    res_web = app_with_test_routes.get("/web/test-ownership-error")
    assert res_web.status_code == 403
    assert "403 Proibido" in res_web.text
    assert "Acesso proibido pela regra de posse" in res_web.text


@pytest.mark.unit
def test_unauthorized_handler(app_with_test_routes: TestClient) -> None:
    """Verifica respostas JSON (401) e Redirect (303) do handler de UnauthorizedError."""
    # 1. API: JSON 401 com cabeçalho WWW-Authenticate
    res_api = app_with_test_routes.get("/api/test-unauthorized-error")
    assert res_api.status_code == 401
    assert res_api.headers.get("www-authenticate") == "Bearer"
    assert res_api.json()["detail"] == "Token expirado ou ausente"

    # 2. Web: 303 See Other redirecionando para /auth/login
    res_web = app_with_test_routes.get("/web/test-unauthorized-error", follow_redirects=False)
    assert res_web.status_code == 303
    assert res_web.headers.get("location") == "/auth/login"
