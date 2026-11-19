"""Testes de integração para os repositórios SQLAlchemy de Materiais Didáticos Locais."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.persistence.repositories import (
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import KnowledgeSource, StudyMap, StudyNode, Subject, Topic, User
from src.infrastructure.database import Base


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
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
def test_knowledge_repository_source_lifecycle_and_nn_topics(db_session: Session) -> None:
    """Valida ciclo completo de persistência, atualização N:N e exclusão de KnowledgeSource."""
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db_session)

    user = User(google_sub="local:know@test.com", email="know@test.com", name="Author")
    user_repo.save(user)
    subj = Subject(name="Direito", owner_id=user.id)
    subj_repo.save(subj)
    topic1 = Topic(subject_id=subj.id, name="Contratos")
    topic2 = Topic(subject_id=subj.id, name="Obrigações")
    top_repo.save(topic1)
    top_repo.save(topic2)

    # 1. Salvar fonte com raw_text local
    raw_content = (
        "Cláusula penal, arras compensatórias e rescisão contratual por inadimplemento absoluto."
    )
    source = KnowledgeSource(
        topic_id=topic1.id,
        title="Livro de Contratos",
        content_type="BOOK_CHAPTER",
        total_chunks=0,
        char_count=len(raw_content),
        raw_text=raw_content,
    )
    saved = source_repo.save(source)
    assert saved.title == "Livro de Contratos"
    assert saved.raw_text == raw_content
    assert saved.char_count == len(raw_content)
    assert saved.topic_ids == (topic1.id,)

    # 2. Buscar por ID e listar por tema
    fetched = source_repo.get_by_id(source.id)
    assert fetched is not None
    assert fetched.id == source.id
    assert fetched.raw_text == raw_content

    sources = source_repo.list_by_topic(topic1.id)
    assert len(sources) == 1
    assert sources[0].id == source.id

    # 3. Atualizar fonte existente e associar a múltiplos temas (N:N)
    updated_source = KnowledgeSource(
        id=source.id,
        title="Livro de Contratos - 2ª Edição",
        topic_ids=(topic1.id, topic2.id),
        content_type="BOOK_CHAPTER",
        total_chunks=0,
        char_count=len(raw_content),
        raw_text=raw_content,
    )
    updated = source_repo.save(updated_source)
    assert updated.title == "Livro de Contratos - 2ª Edição"
    assert set(updated.topic_ids) == {topic1.id, topic2.id}
    assert len(source_repo.list_by_topic(topic2.id)) == 1

    # 4. Deletar fonte
    assert source_repo.delete(source.id) is True
    assert source_repo.get_by_id(source.id) is None
    assert source_repo.list_by_topic(topic1.id) == []
    assert source_repo.list_by_topic(topic2.id) == []
    assert source_repo.delete(uuid4()) is False


@pytest.mark.integration
def test_knowledge_repository_multi_topic_and_node_isolation(db_session: Session) -> None:
    """Garante isolamento por tema e suporte a list_by_node para materiais de StudyNode."""
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)

    user = User(google_sub="local:iso@test.com", email="iso@test.com", name="Author")
    user_repo.save(user)
    subj = Subject(name="Direito", owner_id=user.id)
    subj_repo.save(subj)

    topic_a = Topic(subject_id=subj.id, name="Direito Penal")
    top_repo.save(topic_a)
    topic_b = Topic(subject_id=subj.id, name="Biologia")
    top_repo.save(topic_b)

    s_a = KnowledgeSource(
        topic_id=topic_a.id,
        title="Código Penal",
        raw_text="Habeas corpus e crimes contra o patrimônio.",
        char_count=41,
    )
    source_repo.save(s_a)

    s_b = KnowledgeSource(
        topic_id=topic_b.id,
        title="Biologia Molecular",
        raw_text="Mitose e Meiose celular em organismos eucariontes.",
        char_count=50,
    )
    source_repo.save(s_b)

    # Busca no Tema A deve retornar estritamente s_a e NUNCA s_b
    results_a = source_repo.list_by_topic(topic_a.id)
    assert len(results_a) == 1
    assert results_a[0].id == s_a.id

    # Material vinculado a StudyNode
    study_map = StudyMap(owner_id=user.id, title="Mapa Penal")
    map_repo.save(study_map)
    node_1 = StudyNode(map_id=study_map.id, title="Nó 1")
    node_2 = StudyNode(map_id=study_map.id, title="Nó 2")
    node_repo.save(node_1)
    node_repo.save(node_2)

    s_node = KnowledgeSource(
        title="Resumo do Nó 1",
        node_id=node_1.id,
        raw_text="Anotação local vinculada diretamente ao nó 1 da árvore.",
        char_count=55,
    )
    source_repo.save(s_node)

    node1_sources = source_repo.list_by_node(node_1.id)
    assert len(node1_sources) == 1
    assert node1_sources[0].id == s_node.id
    assert source_repo.list_by_node(node_2.id) == []


@pytest.mark.unit
def test_knowledge_source_mapper_legacy_fallback() -> None:
    """Valida compatibilidade de mapeamento para registros legados sem tabela N:N populada."""
    from src.adapters.persistence.mappers import KnowledgeSourceMapper
    from src.adapters.persistence.models import KnowledgeSourceModel

    tid = uuid4()
    legacy_model = KnowledgeSourceModel(
        id=uuid4(),
        topic_id=tid,
        title="Fonte Legado",
    )
    legacy_model.topics = []
    domain = KnowledgeSourceMapper.to_domain(legacy_model)
    assert domain.topic_ids == (tid,)
