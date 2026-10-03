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
    app.include_router(web_router)
    app.include_router(api_router)

    return app


app = create_app()
