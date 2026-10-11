"""Contratos para clientes de autenticação e tokens (Camada 2 - Aplicação)."""

from typing import Protocol
from uuid import UUID

from src.application.dto.auth_dto import GoogleUserInfoDTO, SessionPayloadDTO


class IGoogleAuthClient(Protocol):
    """Porta para interação com os serviços de identidade do Google (OIDC / OAuth 2.0)."""

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Monta a URL de consentimento OAuth do Google com escopos mínimos."""
        ...

    def exchange_code_for_user_info(self, code: str, redirect_uri: str) -> GoogleUserInfoDTO:
        """Troca o authorization code por tokens e obtém as claims do usuário."""
        ...

    def verify_id_token(self, id_token: str) -> GoogleUserInfoDTO:
        """Valida a assinatura criptográfica de um id_token JWT e extrai as claims."""
        ...


class ISessionTokenService(Protocol):
    """Porta para emissão e validação de tokens de sessão stateless criptografados."""

    def create_session_token(self, user_id: UUID, email: str) -> str:
        """Cifra o payload da sessão com AES-256-GCM gerando um token seguro."""
        ...

    def verify_session_token(self, token: str) -> SessionPayloadDTO | None:
        """Decifra e valida a integridade, autenticidade e expiração do token de sessão."""
        ...

    def create_oauth_state(self, next_url: str = "") -> str:
        """Gera um state CSRF criptografado contendo o timestamp e a rota de retorno."""
        ...

    def verify_oauth_state(self, state: str) -> str | None:
        """Valida o state CSRF e recupera a rota de retorno next_url caso válido."""
        ...
