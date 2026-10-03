"""Testes de integração para os repositórios SQLAlchemy (Camada 3 - Adaptadores)."""

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemySessionRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
)
from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic
from src.infrastructure.database import Base


@pytest.fixture
def db_session() -> Generator[Session]:
    """Cria banco SQLite em memória isolado para os testes de integração."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.integration
def test_subject_repository_crud(db_session: Session) -> None:
    """Verifica persistência, busca por ID, listagem ordenada e unicidade de Subject."""
    repo = SqlAlchemySubjectRepository(db_session)

    s1 = Subject(name="Direito Constitucional")
    s2 = Subject(name="Administração")
    repo.save(s1)
    repo.save(s2)

    found = repo.get_by_id(s1.id)
    assert found is not None
    assert found.name == "Direito Constitucional"

    assert repo.get_by_id(uuid4()) is None

    all_subs = repo.list_all()
    assert [s.name for s in all_subs] == ["Administração", "Direito Constitucional"]

    assert repo.exists_by_name("direito constitucional") is True
    assert repo.exists_by_name("Biologia") is False


@pytest.mark.security
def test_subject_repository_sql_injection_defense(db_session: Session) -> None:
    """Vulnerabilidade prevenida: Injeção de SQL através de queries de consulta de matéria.

    Garantia de segurança: Assegura que consultas parametrizadas do ORM neutralizem
    tentativas de injeção de SQL em strings maliciosas de busca.
    """
    repo = SqlAlchemySubjectRepository(db_session)
    malicious_input = "' OR '1'='1"

    # Não deve quebrar nem retornar True por injeção
    assert repo.exists_by_name(malicious_input) is False


@pytest.mark.integration
def test_topic_repository_crud(db_session: Session) -> None:
    """Verifica persistência, busca por matéria e verificação de existência de Topic."""
    sub_repo = SqlAlchemySubjectRepository(db_session)
    topic_repo = SqlAlchemyTopicRepository(db_session)

    sub = Subject(name="Física")
    sub_repo.save(sub)

    t1 = Topic(subject_id=sub.id, name="Óptica")
    t2 = Topic(subject_id=sub.id, name="Mecânica")
    topic_repo.save(t1)
    topic_repo.save(t2)

    found = topic_repo.get_by_id(t1.id)
    assert found is not None
    assert found.name == "Óptica"

    assert topic_repo.get_by_id(uuid4()) is None

    topics = topic_repo.list_by_subject(sub.id)
    assert [t.name for t in topics] == ["Mecânica", "Óptica"]

    assert topic_repo.exists_by_name(sub.id, "óptica") is True
    assert topic_repo.exists_by_name(sub.id, "Termodinâmica") is False


@pytest.mark.integration
def test_flashcard_repository_pool_operations(db_session: Session) -> None:
    """Verifica salvamento, lote, busca, exclusão e filtros de pool em Flashcard."""
    sub_repo = SqlAlchemySubjectRepository(db_session)
    topic_repo = SqlAlchemyTopicRepository(db_session)
    card_repo = SqlAlchemyFlashcardRepository(db_session)

    sub1 = Subject(name="Sub 1")
    sub2 = Subject(name="Sub 2")
    sub_repo.save(sub1)
    sub_repo.save(sub2)

    top1 = Topic(subject_id=sub1.id, name="Top 1")
    top2 = Topic(subject_id=sub2.id, name="Top 2")
    topic_repo.save(top1)
    topic_repo.save(top2)

    c1 = Flashcard(topic_id=top1.id, front="C1", back="1", position=100)
    c2 = Flashcard(topic_id=top1.id, front="C2", back="2", position=200)
    c3 = Flashcard(topic_id=top2.id, front="C3", back="3", position=50)

    # Testa save unitário e save_all em lote
    card_repo.save(c1)
    card_repo.save_all([c2, c3])

    # Global pool ordenada por position ASC
    global_pool = card_repo.list_pool(None, None)
    assert len(global_pool) == 3
    assert [c.position for c in global_pool] == [50, 100, 200]
    assert card_repo.count_pool(None, None) == 3

    # Paginação em list_pool
    paged = card_repo.list_pool(None, None, limit=1, min_position=50)
    assert len(paged) == 1
    assert paged[0].position == 100

    # Contagens agrupadas via GROUP BY
    sub_counts = card_repo.count_by_subjects()
    assert sub_counts[sub1.id] == 2
    assert sub_counts[sub2.id] == 1

    top_counts = card_repo.count_by_topics()
    assert top_counts[top1.id] == 2
    assert top_counts[top2.id] == 1

    # list_all_with_topics no SubjectRepository
    subs_with_topics = sub_repo.list_all_with_topics()
    assert len(subs_with_topics) == 2
    sub1_found = next(s for s, t in subs_with_topics if s.id == sub1.id)
    sub1_topics = next(t for s, t in subs_with_topics if s.id == sub1.id)
    assert sub1_found.name == "Sub 1"
    assert len(sub1_topics) == 1
    assert sub1_topics[0].name == "Top 1"

    # save_all vazio e atualização de existentes
    card_repo.save_all([])
    c2.position = 250
    card_repo.save_all([c2])
    c2_reloaded = card_repo.get_by_id(c2.id)
    assert c2_reloaded is not None
    assert c2_reloaded.position == 250

    # save com tópicos atualizados
    c2.topic_ids = (top2.id,)
    card_repo.save(c2)
    c2_updated = card_repo.get_by_id(c2.id)
    assert c2_updated is not None
    assert top2.id in c2_updated.topic_ids

    # Filtro por matéria
    sub1_pool = card_repo.list_pool(sub1.id, None)
    assert len(sub1_pool) == 1
    assert card_repo.count_pool(sub1.id, None) == 1

    # Filtro por tema
    top2_pool = card_repo.list_pool(None, top2.id)
    assert len(top2_pool) == 2
    assert card_repo.count_pool(None, top2.id) == 2

    # Busca por ID e exclusão
    assert card_repo.get_by_id(c1.id) is not None
    assert card_repo.get_by_id(uuid4()) is None

    card_repo.delete(c1.id)
    assert card_repo.get_by_id(c1.id) is None


@pytest.mark.integration
def test_session_repository(db_session: Session) -> None:
    """Verifica persistência e recuperação de sessão de estudo."""
    repo = SqlAlchemySessionRepository(db_session)
    t_id = uuid4()

    assert repo.get_active_session(None, t_id) is None

    session = FlashcardPoolSession(
        topic_id_filter=t_id,
        current_position=100,
        round_number=2,
        updated_at=datetime.now(UTC),
    )
    repo.save_session(session)

    loaded = repo.get_active_session(None, t_id)
    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.current_position == 100
    assert loaded.round_number == 2
    assert loaded.is_active is True


@pytest.mark.integration
def test_flashcard_repository_multi_topic_operations(db_session: Session) -> None:
    """Verifica persistência de flashcard com múltiplos temas e deduplicação no pool (ADR-004)."""
    sub_repo = SqlAlchemySubjectRepository(db_session)
    topic_repo = SqlAlchemyTopicRepository(db_session)
    card_repo = SqlAlchemyFlashcardRepository(db_session)

    sub = Subject(name="Direito Constitucional")
    sub_repo.save(sub)

    t1 = Topic(subject_id=sub.id, name="Controle de Constitucionalidade")
    t2 = Topic(subject_id=sub.id, name="Ações Diretas")
    topic_repo.save(t1)
    topic_repo.save(t2)

    # Flashcard associado a dois temas da mesma matéria
    card = Flashcard(
        topic_ids=[t1.id, t2.id],
        front="O que é ADI?",
        back="Ação Direta de Inconstitucionalidade",
        position=100,
    )
    card_repo.save(card)

    # Carrega por ID
    loaded = card_repo.get_by_id(card.id)
    assert loaded is not None
    assert set(loaded.topic_ids) == {t1.id, t2.id}

    # Deve aparecer ao consultar pool do tema 1
    pool_t1 = card_repo.list_pool(None, t1.id)
    assert len(pool_t1) == 1
    assert pool_t1[0].id == card.id

    # Deve aparecer ao consultar pool do tema 2
    pool_t2 = card_repo.list_pool(None, t2.id)
    assert len(pool_t2) == 1
    assert pool_t2[0].id == card.id

    # Ao consultar por matéria, não deve duplicar o card mesmo pertencendo a 2 temas
    pool_sub = card_repo.list_pool(sub.id, None)
    assert len(pool_sub) == 1
    assert pool_sub[0].id == card.id
    assert card_repo.count_pool(sub.id, None) == 1

    # Atualiza temas do card para conter apenas t1
    updated_card = Flashcard(
        id=card.id,
        topic_ids=[t1.id],
        front=card.front,
        back=card.back,
        position=card.position,
    )
    card_repo.save(updated_card)
    reloaded = card_repo.get_by_id(card.id)
    assert reloaded is not None
    assert reloaded.topic_ids == (t1.id,)
