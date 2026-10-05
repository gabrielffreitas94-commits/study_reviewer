"""Adaptador concreto para armazenamento de sessões efêmeras no Redis (Camada 3 - Adaptadores)."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from src.application.ports.session_store import ISessionStore
from src.domain.entities import FlashcardPoolSession


class RedisSessionRepository(ISessionStore):
    """Repositório de sessões efêmeras utilizando Redis assíncrono (redis.asyncio)."""

    def __init__(self, redis_client: Any, tenant_id: str = "default") -> None:
        self._redis = redis_client
        self._tenant_id = tenant_id

    def _session_key(self, user_id: UUID, session_id: UUID) -> str:
        return f"tenant:{self._tenant_id}:user:{user_id}:session:{session_id}:queue"

    def _meta_key(self, session_id: UUID) -> str:
        return f"tenant:{self._tenant_id}:session_meta:{session_id}"

    def _active_index_key(
        self, user_id: UUID, subject_id: UUID | None, topic_id: UUID | None
    ) -> str:
        sub_str = str(subject_id) if subject_id else "all"
        top_str = str(topic_id) if topic_id else "all"
        return f"tenant:{self._tenant_id}:user:{user_id}:active_session:sub_{sub_str}:top_{top_str}"

    @staticmethod
    def _serialize_session(session: FlashcardPoolSession) -> str:
        payload = {
            "id": str(session.id),
            "user_id": str(session.user_id),
            "subject_id": str(session.subject_id) if session.subject_id else None,
            "topic_id_filter": str(session.topic_id_filter) if session.topic_id_filter else None,
            "round_number": session.round_number,
            "current_index": session.current_index,
            "card_queue": [str(uid) for uid in session.card_queue],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "subject_id_filter": (
                str(session.subject_id_filter) if session.subject_id_filter else None
            ),
            "current_position": session.current_position,
            "is_active": session.is_active,
        }
        return json.dumps(payload)

    @staticmethod
    def _deserialize_session(raw_data: str | bytes) -> FlashcardPoolSession:
        text = raw_data if isinstance(raw_data, str) else raw_data.decode("utf-8")
        data = json.loads(text)
        return FlashcardPoolSession(
            id=UUID(data["id"]),
            user_id=UUID(data["user_id"]),
            subject_id=UUID(data["subject_id"]) if data.get("subject_id") else None,
            topic_id_filter=(
                UUID(data["topic_id_filter"]) if data.get("topic_id_filter") else None
            ),
            round_number=int(data.get("round_number", 1)),
            current_index=int(data.get("current_index", 0)),
            card_queue=[UUID(uid) for uid in data.get("card_queue", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            subject_id_filter=(
                UUID(data["subject_id_filter"]) if data.get("subject_id_filter") else None
            ),
            current_position=int(data.get("current_position", 0)),
            is_active=bool(data.get("is_active", True)),
        )

    async def save_session(self, session: FlashcardPoolSession, ttl_seconds: int = 86400) -> None:
        """Salva a sessão efêmera e seus índices com TTL estrito de 24h."""
        s_key = self._session_key(session.user_id, session.id)
        m_key = self._meta_key(session.id)
        idx_key = self._active_index_key(
            session.user_id, session.subject_id, session.topic_id_filter
        )
        serialized = self._serialize_session(session)

        # Salva a sessão, o ponteiro de metadados e o índice de sessão ativa
        await self._redis.set(s_key, serialized, ex=ttl_seconds)
        await self._redis.set(m_key, str(session.user_id), ex=ttl_seconds)
        await self._redis.set(idx_key, str(session.id), ex=ttl_seconds)

    async def get_session(self, session_id: UUID) -> FlashcardPoolSession | None:
        """Busca sessão por UUID utilizando o índice de metadados."""
        m_key = self._meta_key(session_id)
        user_id_raw = await self._redis.get(m_key)
        if not user_id_raw:
            return None

        user_id_str = user_id_raw if isinstance(user_id_raw, str) else user_id_raw.decode("utf-8")
        s_key = self._session_key(UUID(user_id_str), session_id)
        raw_session = await self._redis.get(s_key)
        if not raw_session:
            return None

        return self._deserialize_session(raw_session)

    async def get_active_session(
        self, user_id: UUID, subject_id: UUID | None, topic_id: UUID | None
    ) -> FlashcardPoolSession | None:
        """Recupera a sessão ativa para a combinação de usuário e filtros."""
        idx_key = self._active_index_key(user_id, subject_id, topic_id)
        session_id_raw = await self._redis.get(idx_key)
        if not session_id_raw:
            return None

        session_id_str = (
            session_id_raw if isinstance(session_id_raw, str) else session_id_raw.decode("utf-8")
        )
        return await self.get_session(UUID(session_id_str))

    async def delete_session(self, session_id: UUID) -> None:
        """Remove a sessão e seus índices associados."""
        m_key = self._meta_key(session_id)
        user_id_raw = await self._redis.get(m_key)
        if user_id_raw:
            user_id_str = (
                user_id_raw if isinstance(user_id_raw, str) else user_id_raw.decode("utf-8")
            )
            s_key = self._session_key(UUID(user_id_str), session_id)
            raw_session = await self._redis.get(s_key)
            if raw_session:
                session = self._deserialize_session(raw_session)
                idx_key = self._active_index_key(
                    session.user_id, session.subject_id, session.topic_id_filter
                )
                await self._redis.delete(idx_key)
            await self._redis.delete(s_key)
        await self._redis.delete(m_key)

    async def purge_user_sessions(self, user_id: UUID) -> int:
        """Remove todas as chaves de sessão do usuário e metadados (LGPD Art. 18)."""
        pattern = f"tenant:{self._tenant_id}:user:{user_id}:*"
        keys: list[Any] = []
        meta_keys: list[str] = []

        async for key in self._redis.scan_iter(match=pattern):
            keys.append(key)
            key_str = key if isinstance(key, str) else key.decode("utf-8")
            if ":session:" in key_str and key_str.endswith(":queue"):
                parts = key_str.split(":")
                if len(parts) >= 6:
                    sess_id_str = parts[5]
                    meta_keys.append(self._meta_key(UUID(sess_id_str)))

        all_keys = list(keys) + meta_keys
        if all_keys:
            await self._redis.delete(*all_keys)
        return len(all_keys)
