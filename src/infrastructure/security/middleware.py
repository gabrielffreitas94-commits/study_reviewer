"""Middleware de cabeçalhos de segurança HTTP (Camada 4 - Infraestrutura)."""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona cabeçalhos de segurança defensivos a todas as respostas HTTP."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        # Prevenção de MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevenção de Clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Controle de Referrer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrição de APIs de hardware sensíveis
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content Security Policy defensiva permitindo CDNs legítimos e scripts inline do HTMX
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https:;"
        )

        return response
