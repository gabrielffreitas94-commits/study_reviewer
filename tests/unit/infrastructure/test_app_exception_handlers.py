"""Testes unitários para os manipuladores de exceções da aplicação FastAPI (Sprint 02)."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.domain.exceptions import (
    QuestionNotDueError,
    QuestionNotFoundError,
    ResourceOwnershipError,
    UnauthorizedError,
)
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

    @app.get("/api/test-question-not-found")
    def api_question_not_found() -> None:
        raise QuestionNotFoundError("Pergunta não encontrada")

    @app.get("/web/test-question-not-found")
    def web_question_not_found() -> None:
        raise QuestionNotFoundError("Pergunta não encontrada")

    @app.get("/api/test-question-not-due")
    def api_question_not_due() -> None:
        raise QuestionNotDueError("Pergunta ainda não vencida")

    @app.get("/web/test-question-not-due")
    def web_question_not_due() -> None:
        raise QuestionNotDueError("Pergunta ainda não vencida")

    @app.get("/api/test-unhandled-exception")
    def api_unhandled() -> None:
        raise RuntimeError("Crash inesperado")

    @app.get("/web/test-unhandled-exception")
    def web_unhandled() -> None:
        raise RuntimeError("Crash inesperado")

    with TestClient(app, raise_server_exceptions=False) as client:
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


@pytest.mark.unit
def test_question_not_found_handler(app_with_test_routes: TestClient) -> None:
    """Verifica respostas JSON (404) e HTML (404) do handler de QuestionNotFoundError."""
    res_api = app_with_test_routes.get("/api/test-question-not-found")
    assert res_api.status_code == 404
    assert res_api.json()["detail"] == "Pergunta não encontrada"

    res_web = app_with_test_routes.get("/web/test-question-not-found")
    assert res_web.status_code == 404
    assert "404 Não Encontrado" in res_web.text


@pytest.mark.unit
def test_question_not_due_handler(app_with_test_routes: TestClient) -> None:
    """Verifica respostas JSON (400) e HTML (400) do handler de QuestionNotDueError."""
    res_api = app_with_test_routes.get("/api/test-question-not-due")
    assert res_api.status_code == 400
    assert res_api.json()["detail"] == "Pergunta ainda não vencida"

    res_web = app_with_test_routes.get("/web/test-question-not-due")
    assert res_web.status_code == 400
    assert "400 Requisição Inválida" in res_web.text


@pytest.mark.unit
def test_global_exception_handler(app_with_test_routes: TestClient) -> None:
    """Verifica respostas JSON (500) e HTML (500) do handler global de exceções não tratadas."""
    res_api = app_with_test_routes.get("/api/test-unhandled-exception")
    assert res_api.status_code == 500
    assert res_api.json()["detail"] == "Internal Server Error"

    res_web = app_with_test_routes.get("/web/test-unhandled-exception")
    assert res_web.status_code == 500
    assert "500 Erro Interno do Servidor" in res_web.text


@pytest.mark.unit
def test_health_check_endpoint(app_with_test_routes: TestClient) -> None:
    """Verifica que o endpoint /health retorna 200 e payload esperado."""
    res = app_with_test_routes.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


@pytest.mark.unit
def test_health_logs_endpoint(app_with_test_routes: TestClient) -> None:
    """Verifica que o endpoint /health/logs retorna 200 em formato JSON e texto."""
    # 1. JSON default
    res = app_with_test_routes.get("/health/logs?limit=50")
    assert res.status_code == 200
    data = res.json()
    assert "environment" in data
    assert "total_buffered" in data
    assert "logs" in data
    assert isinstance(data["logs"], list)

    # 2. Text format
    res_text = app_with_test_routes.get("/health/logs?format=text&limit=10")
    assert res_text.status_code == 200
    assert "text/plain" in res_text.headers.get("content-type", "")
