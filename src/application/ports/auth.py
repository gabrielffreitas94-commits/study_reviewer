"""Contratos para clientes de autenticação, hash de senha e tokens (Camada 2 - Aplicação)."""

from typing import Protocol
from uuid import UUID

from src.application.dto.auth_dto import SessionPayloadDTO


class IPasswordHasher(Protocol):
    """Porta para geração e verificação segura de hashes de senha."""

    def hash_password(self, password: str) -> str:
        """Gera um hash criptográfico com salt aleatório para a senha informada."""
        ...

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verifica em tempo constante se a senha corresponde ao hash armazenado."""
        ...


class ISessionTokenService(Protocol):
    """Porta para emissão e validação de tokens de sessão stateless criptografados."""

    def create_session_token(self, user_id: UUID, email: str) -> str:
        """Cifra o payload da sessão com AES-256-GCM gerando um token seguro."""
        ...

    def verify_session_token(self, token: str) -> SessionPayloadDTO | None:
        """Decifra e valida a integridade, autenticidade e expiração do token de sessão."""
        ...
