"""Testes de integração para os repositórios SQLAlchemy de Base de Conhecimento e Chunks."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.persistence.repositories import (
    SqlAlchemyKnowledgeChunkRepository,
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import KnowledgeChunk, KnowledgeSource, Subject, Topic, User
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
def test_knowledge_repository_source_and_chunk_lifecycle(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db_session)
    chunk_repo = SqlAlchemyKnowledgeChunkRepository(db_session)

    user = User(google_sub="sub-know-1", email="know@test.com", name="Author")
    user_repo.save(user)
    subj = Subject(name="Direito", owner_id=user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Contratos")
    top_repo.save(topic)

    # 1. Salvar fonte
    source = KnowledgeSource(
        topic_id=topic.id,
        title="Livro de Contratos",
        content_type="BOOK_CHAPTER",
        total_chunks=2,
        char_count=3500,
    )
    saved = source_repo.save(source)
    assert saved.title == "Livro de Contratos"

    # 2. Buscar por ID e listar por tema
    fetched = source_repo.get_by_id(source.id)
    assert fetched is not None
    assert fetched.id == source.id

    sources = source_repo.list_by_topic(topic.id)
    assert len(sources) == 1
    assert sources[0].id == source.id

    # 3. Atualizar fonte existente
    source.title = "Livro de Contratos - 2ª Edição"
    updated = source_repo.save(source)
    assert updated.title == "Livro de Contratos - 2ª Edição"

    # 4. Salvar chunks
    c1 = KnowledgeChunk(
        source_id=source.id,
        topic_id=topic.id,
        chunk_index=0,
        content="Cláusula penal e arras compensatórias.",
        embedding=(1.0, 0.0, 0.0),
    )
    c2 = KnowledgeChunk(
        source_id=source.id,
        topic_id=topic.id,
        chunk_index=1,
        content="Rescisão contratual por inadimplemento.",
        embedding=(0.0, 1.0, 0.0),
    )
    chunk_repo.save_batch([c1, c2])

    chunks = chunk_repo.list_by_topic(topic.id)
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1

    # 5. Busca por similaridade
    query_vec = [1.0, 0.0, 0.0]
    similar = chunk_repo.search_similar(topic.id, query_vec, top_k=1)
    assert len(similar) == 1
    assert similar[0][0].id == c1.id
    assert pytest.approx(similar[0][1], 0.01) == 1.0

    # 6. Deletar chunks por fonte
    deleted_chunks = chunk_repo.delete_by_source(source.id)
    assert deleted_chunks == 2
    assert len(chunk_repo.list_by_topic(topic.id)) == 0

    # 7. Deletar fonte
    assert source_repo.delete(source.id) is True
    assert source_repo.get_by_id(source.id) is None
    assert source_repo.delete(uuid4()) is False


@pytest.mark.integration
def test_knowledge_repository_multi_topic_isolation(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db_session)
    chunk_repo = SqlAlchemyKnowledgeChunkRepository(db_session)

    user = User(google_sub="sub-know-iso", email="iso@test.com", name="Author")
    user_repo.save(user)
    subj = Subject(name="Direito", owner_id=user.id)
    subj_repo.save(subj)

    topic_a = Topic(subject_id=subj.id, name="Direito Penal")
    top_repo.save(topic_a)
    topic_b = Topic(subject_id=subj.id, name="Biologia")
    top_repo.save(topic_b)

    s_a = KnowledgeSource(topic_id=topic_a.id, title="Código Penal")
    source_repo.save(s_a)
    c_a = KnowledgeChunk(
        source_id=s_a.id,
        topic_id=topic_a.id,
        chunk_index=0,
        content="Habeas corpus e crimes contra o patrimônio.",
        embedding=(1.0, 0.0, 0.0),
    )
    chunk_repo.save_batch([c_a])

    s_b = KnowledgeSource(topic_id=topic_b.id, title="Biologia Molecular")
    source_repo.save(s_b)
    c_b = KnowledgeChunk(
        source_id=s_b.id,
        topic_id=topic_b.id,
        chunk_index=0,
        content="Mitose e Meiose celular.",
        embedding=(1.0, 0.0, 0.0),  # mesmo vetor propositalmente
    )
    chunk_repo.save_batch([c_b])

    # Busca no Tema A deve retornar estritamente c_a e NUNCA c_b
    results_a = chunk_repo.search_similar(topic_a.id, [1.0, 0.0, 0.0], top_k=5)
    assert len(results_a) == 1
    assert results_a[0][0].id == c_a.id

    # Busca no Tema B deve retornar estritamente c_b e NUNCA c_a
    results_b = chunk_repo.search_similar(topic_b.id, [1.0, 0.0, 0.0], top_k=5)
    assert len(results_b) == 1
    assert results_b[0][0].id == c_b.id
