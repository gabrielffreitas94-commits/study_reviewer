"""DTOs para Autenticação e Usuários (Clean Architecture - Camada 2)."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class GoogleAuthInputDTO:
    """Dados de entrada para autenticação via Google OIDC."""

    code: str | None = None
    id_token: str | None = None
    redirect_uri: str = ""


@dataclass(frozen=True)
class GoogleUserInfoDTO:
    """Claims extraídas com segurança a partir do ID Token ou UserInfo do Google."""

    sub: str
    email: str
    name: str
    avatar_url: str | None = None


@dataclass(frozen=True)
class SessionPayloadDTO:
    """Payload decifrado de um token de sessão criptografado."""

    user_id: UUID
    email: str
    iat: int
    exp: int


@dataclass(frozen=True)
class AuthResultDTO:
    """Resultado retornado após autenticação bem-sucedida."""

    user_id: UUID
    email: str
    name: str
    avatar_url: str | None
    session_token: str
    is_new_user: bool


@dataclass(frozen=True)
class UserDTO:
    """Representação de saída dos dados do usuário ativo."""

    id: UUID
    email: str
    name: str
    avatar_url: str | None
    created_at: date
