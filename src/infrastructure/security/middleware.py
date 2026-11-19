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

        # Content Security Policy estritamente offline ('self')
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self' data:;"
        )

        return response
