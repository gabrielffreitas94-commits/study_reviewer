"""Injeção de dependências de segurança e autenticação para o FastAPI.

Camada 4 - Infraestrutura.
"""

import urllib.parse

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import SqlAlchemyUserRepository
from src.application.ports.auth import IGoogleAuthClient, ISessionTokenService
from src.domain.entities import User
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.security.google_client import GoogleOAuthClient
from src.infrastructure.security.session_service import AesGcmSessionTokenService

_session_service = AesGcmSessionTokenService(settings.SECRET_KEY)
_google_client = GoogleOAuthClient(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)


def get_session_service() -> ISessionTokenService:
    """Retorna o serviço singleton de tokens de sessão AES-256-GCM."""
    return _session_service


def get_google_client() -> IGoogleAuthClient:
    """Retorna o cliente de integração com o Google OIDC."""
    return _google_client


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    session_service: ISessionTokenService = Depends(get_session_service),
) -> User | None:
    """Resolve o usuário autenticado caso um token válido seja enviado, ou retorna None."""
    token: str | None = None

    # 1. Verifica header Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    # 2. Caso não esteja no header, verifica cookie de sessão
    if not token:
        token = request.cookies.get("session_token")

    if not token:
        return None

    payload = session_service.verify_session_token(token)
    if payload is None:
        return None

    user_repo = SqlAlchemyUserRepository(db)
    return user_repo.get_by_id(payload.user_id)


def get_current_user(
    request: Request,
    user: User | None = Depends(get_current_user_optional),
) -> User:
    """Exige autenticação obrigatória; lança 401 para API ou redireciona para login na Web."""
    if user is not None:
        return user

    path = request.url.path
    next_param = urllib.parse.quote(str(request.url.path), safe="")

    # Consumo via API REST
    if path.startswith("/api/"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado. Forneça um Bearer Token válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Requisição parcial HTMX
    if request.headers.get("HX-Request") == "true":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada.",
            headers={"HX-Redirect": f"/auth/login?next={next_param}"},
        )

    # Navegação Web normal: redireciona para tela de login preservando a rota de destino
    raise HTTPException(
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"Location": f"/auth/login?next={next_param}"},
    )
