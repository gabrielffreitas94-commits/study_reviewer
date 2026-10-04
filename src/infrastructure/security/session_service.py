"""Serviço de emissão e validação de tokens de sessão stateless via AES-256-GCM (Camada 4)."""

import hashlib
import json
import time
from uuid import UUID

from src.application.dto.auth_dto import SessionPayloadDTO
from src.application.ports.auth import ISessionTokenService
from src.infrastructure.security.crypto import AES256GCMCipher, CryptoError


class AesGcmSessionTokenService(ISessionTokenService):
    """Implementa ISessionTokenService utilizando criptografia simétrica autenticada AES-256-GCM."""

    DEFAULT_TTL_SECONDS = 30 * 24 * 3600  # 30 dias

    def __init__(self, secret_key: str | bytes, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        if isinstance(secret_key, str):
            key_bytes = hashlib.sha256(secret_key.encode("utf-8")).digest()
        else:
            key_bytes = secret_key
        self._cipher = AES256GCMCipher(key_bytes)
        self._ttl_seconds = ttl_seconds

    def create_session_token(self, user_id: UUID, email: str) -> str:
        now = int(time.time())
        exp = now + self._ttl_seconds
        payload = {
            "user_id": str(user_id),
            "email": email,
            "iat": now,
            "exp": exp,
        }
        plaintext = json.dumps(payload)
        return self._cipher.encrypt(plaintext)

    def verify_session_token(self, token: str) -> SessionPayloadDTO | None:
        try:
            plaintext = self._cipher.decrypt(token)
            data = json.loads(plaintext)
            now = int(time.time())
            if data.get("exp", 0) <= now:
                return None
            return SessionPayloadDTO(
                user_id=UUID(data["user_id"]),
                email=data["email"],
                iat=data["iat"],
                exp=data["exp"],
            )
        except (CryptoError, ValueError, KeyError, json.JSONDecodeError):
            return None

    def create_oauth_state(self, next_url: str = "") -> str:
        """Gera um state CSRF criptografado contendo o timestamp e a rota de retorno."""
        now = int(time.time())
        payload = {
            "type": "oauth_state",
            "next": next_url,
            "exp": now + 600,  # 10 minutos
        }
        return self._cipher.encrypt(json.dumps(payload))

    def verify_oauth_state(self, state: str) -> str | None:
        """Valida o state CSRF e recupera a rota de retorno next_url caso válido."""
        try:
            plaintext = self._cipher.decrypt(state)
            data = json.loads(plaintext)
            now = int(time.time())
            if data.get("type") != "oauth_state" or data.get("exp", 0) <= now:
                return None
            return str(data.get("next", ""))
        except (CryptoError, ValueError, KeyError, json.JSONDecodeError):
            return None
