"""DTOs para Autenticação e Usuários (Clean Architecture - Camada 2)."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(slots=True, frozen=True)
class LocalRegisterInputDTO:
    """Dados de entrada para cadastro de conta local."""

    email: str
    name: str
    password: str


@dataclass(slots=True, frozen=True)
class LocalLoginInputDTO:
    """Dados de entrada para autenticação local via e-mail e senha."""

    email: str
    password: str


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
