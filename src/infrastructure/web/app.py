"""Fábrica da aplicação FastAPI (Camada 4 - Frameworks & Drivers)."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.api.controllers import api_router
from src.adapters.web.controllers import web_router
from src.infrastructure.config import settings
from src.infrastructure.database import Base, engine
from src.infrastructure.security.middleware import SecurityHeadersMiddleware

logger = logging.getLogger("study_reviewer")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Gerencia o ciclo de vida da aplicação (startup e shutdown)."""
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    """Cria e configura a instância do FastAPI com middlewares e roteadores."""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=False,
        lifespan=lifespan,
    )

    # Habilita CORS para origens móveis e clientes web
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Adiciona middleware de segurança HTTP
    app.add_middleware(SecurityHeadersMiddleware)

    # Monta arquivos estáticos locais (CSS/JS)
    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).resolve().parent.parent.parent / "adapters" / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Registra rotas web (Jinja2 / HTMX) e API REST (JSON)
    from fastapi import Request
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

    from src.adapters.api.auth_controllers import api_auth_router
    from src.adapters.api.evaluation_controllers import api_evaluation_router
    from src.adapters.api.knowledge_controllers import api_knowledge_router
    from src.adapters.api.performance_controllers import api_performance_router
    from src.adapters.api.question_controllers import api_question_router
    from src.adapters.web.auth_controllers import auth_router, privacy_router
    from src.adapters.web.performance_controllers import web_performance_router
    from src.adapters.web.question_controllers import web_question_router
    from src.domain.exceptions import (
        QuestionNotDueError,
        QuestionNotFoundError,
        ResourceOwnershipError,
        UnauthorizedError,
    )

    @app.exception_handler(ResourceOwnershipError)
    async def resource_ownership_handler(request: Request, exc: ResourceOwnershipError) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=403, content={"detail": str(exc)})
        html_content = (
            "<!DOCTYPE html><html><body>"
            "<h1>403 Proibido</h1>"
            f"<p>{exc}</p>"
            "<a href='/study'>Voltar ao Estudo</a>"
            "</body></html>"
        )
        return HTMLResponse(status_code=403, content=html_content)

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": str(exc)},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return RedirectResponse(url="/auth/login", status_code=303)

    @app.exception_handler(QuestionNotFoundError)
    async def question_not_found_handler(request: Request, exc: QuestionNotFoundError) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=404, content={"detail": str(exc)})
        return HTMLResponse(status_code=404, content=f"<h1>404 Não Encontrado</h1><p>{exc}</p>")

    @app.exception_handler(QuestionNotDueError)
    async def question_not_due_handler(request: Request, exc: QuestionNotDueError) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=400, content={"detail": str(exc)})
        return HTMLResponse(
            status_code=400, content=f"<h1>400 Requisição Inválida</h1><p>{exc}</p>"
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> Response:
        logger.exception(
            "Erro interno não tratado ao processar %s %s: %s",
            request.method,
            request.url.path,
            exc,
        )
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"},
            )
        html_content = (
            "<!DOCTYPE html><html><body>"
            "<h1>500 Erro Interno do Servidor</h1>"
            "<p>Ocorreu um erro inesperado no servidor.</p>"
            "<a href='/study'>Voltar ao Estudo</a>"
            "</body></html>"
        )
        return HTMLResponse(status_code=500, content=html_content)

    app.include_router(auth_router)
    app.include_router(privacy_router)
    app.include_router(api_auth_router)
    app.include_router(web_router)
    app.include_router(api_router)
    app.include_router(web_question_router)
    app.include_router(api_question_router)
    app.include_router(api_knowledge_router)
    app.include_router(api_evaluation_router)
    app.include_router(web_performance_router)
    app.include_router(api_performance_router)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Endpoint público de monitoramento de integridade e liveness (R$ 0,00)."""
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "storage": settings.STUDY_EVENTS_BACKEND,
        }

    return app


app = create_app()
