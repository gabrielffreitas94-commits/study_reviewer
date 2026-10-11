"""Testes unitários para o RedisSessionRepository com fakeredis assíncrono."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import fakeredis.aioredis
import pytest

from src.adapters.persistence.redis_session_repository import RedisSessionRepository
from src.domain.entities import FlashcardPoolSession


@pytest.mark.unit
def test_redis_session_repository_save_and_get() -> None:
    """Valida salvamento e recuperação completa de sessão efêmera no Redis."""

    async def _test() -> None:
        fake_redis = fakeredis.aioredis.FakeRedis()
        repo = RedisSessionRepository(fake_redis, tenant_id="tenant-test")

        user_id = uuid4()
        sub_id = uuid4()
        top_id = uuid4()
        c1, c2 = uuid4(), uuid4()

        session = FlashcardPoolSession(
            user_id=user_id,
            subject_id=sub_id,
            topic_id_filter=top_id,
            round_number=2,
            current_index=1,
            card_queue=[c1, c2],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await repo.save_session(session)

        # Recupera por ID
        recovered = await repo.get_session(session.id)
        assert recovered is not None
        assert recovered.id == session.id
        assert recovered.user_id == user_id
        assert recovered.subject_id == sub_id
        assert recovered.topic_id_filter == top_id
        assert recovered.round_number == 2
        assert recovered.current_index == 1
        assert recovered.card_queue == [c1, c2]

        # Recupera via active_session
        active = await repo.get_active_session(user_id, sub_id, top_id)
        assert active is not None
        assert active.id == session.id

    asyncio.run(_test())


@pytest.mark.unit
def test_redis_session_repository_miss_and_delete() -> None:
    """Valida cenários de cache miss e remoção segura de sessão."""

    async def _test() -> None:
        fake_redis = fakeredis.aioredis.FakeRedis()
        repo = RedisSessionRepository(fake_redis)

        # Sessão inexistente
        non_existent = await repo.get_session(uuid4())
        assert non_existent is None

        # Sessão ativa inexistente
        active_none = await repo.get_active_session(uuid4(), None, None)
        assert active_none is None

        # Meta key órfã (chave de sessão expirou mas meta_key ainda existe)
        orphan_session_id = uuid4()
        await fake_redis.set(f"tenant:default:session_meta:{orphan_session_id}", str(uuid4()))
        assert await repo.get_session(orphan_session_id) is None

        # Salva e deleta
        session = FlashcardPoolSession()
        await repo.save_session(session)
        assert await repo.get_session(session.id) is not None

        await repo.delete_session(session.id)
        assert await repo.get_session(session.id) is None

    asyncio.run(_test())


@pytest.mark.unit
def test_redis_session_repository_purge_user_sessions_lgpd() -> None:
    """Valida expurgo de todas as sessões efêmeras do usuário para LGPD."""

    async def _test() -> None:
        fake_redis = fakeredis.aioredis.FakeRedis()
        repo = RedisSessionRepository(fake_redis)

        user1 = uuid4()
        user2 = uuid4()

        s1 = FlashcardPoolSession(user_id=user1)
        s2 = FlashcardPoolSession(user_id=user1)
        s3 = FlashcardPoolSession(user_id=user2)

        await repo.save_session(s1)
        await repo.save_session(s2)
        await repo.save_session(s3)

        purged_count = await repo.purge_user_sessions(user1)
        assert purged_count >= 2

        # Sessões do user1 foram eliminadas
        assert await repo.get_session(s1.id) is None
        assert await repo.get_session(s2.id) is None

        # Sessão do user2 permanece intacta
        assert await repo.get_session(s3.id) is not None

    asyncio.run(_test())
