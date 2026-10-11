"""Contrato da porta de armazenamento de sessões efêmeras (Clean Architecture - Camada 2)."""

from typing import Protocol
from uuid import UUID

from src.domain.entities import FlashcardPoolSession


class ISessionStore(Protocol):
    """Porta para persistência e recuperação assíncrona de sessões efêmeras em cache."""

    async def get_session(self, session_id: UUID) -> FlashcardPoolSession | None:
        """Recupera uma sessão efêmera por seu UUID."""
        ...

    async def save_session(self, session: FlashcardPoolSession, ttl_seconds: int = 86400) -> None:
        """Armazena a sessão com TTL de 24 horas (86.400 segundos)."""
        ...

    async def delete_session(self, session_id: UUID) -> None:
        """Remove a sessão do cache."""
        ...

    async def get_active_session(
        self, user_id: UUID, subject_id: UUID | None, topic_id: UUID | None
    ) -> FlashcardPoolSession | None:
        """Busca a sessão ativa associada aos filtros de estudo do usuário."""
        ...
