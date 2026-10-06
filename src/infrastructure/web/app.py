"""Fábrica da aplicação FastAPI (Camada 4 - Frameworks & Drivers)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.api.controllers import api_router
from src.adapters.web.controllers import web_router
from src.infrastructure.config import settings
from src.infrastructure.database import Base, engine
from src.infrastructure.security.middleware import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Gerencia o ciclo de vida da aplicação (startup e shutdown)."""
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    """Cria e configura a instância do FastAPI com middlewares e roteadores."""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
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
    from src.adapters.web.auth_controllers import auth_router
    from src.domain.exceptions import ResourceOwnershipError, UnauthorizedError

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

    app.include_router(auth_router)
    app.include_router(api_auth_router)
    app.include_router(web_router)
    app.include_router(api_router)

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
