"""Testes de integração para os repositórios SQLAlchemy da Árvore de Estudos RPG."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemyNodeContentRepository,
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyStudyEdgeRepository,
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import (
    Flashcard,
    KnowledgeSource,
    Question,
    StudyEdge,
    StudyMap,
    StudyNode,
    Subject,
    Topic,
    User,
)
from src.infrastructure.database import Base


@pytest.fixture
def db_session() -> Generator[Session]:
    """Cria banco SQLite em memória isolado para os testes de integração."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.integration
def test_study_map_repository_crud(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)

    user = User(google_sub="sub-tree-1", email="tree1@test.com", name="Tree Explorer")
    user_repo.save(user)

    # 1. Cria mapa raiz
    root_map = StudyMap(
        owner_id=user.id,
        title="Engenharia de Software",
        description="Mapa principal de estudos",
        is_public=True,
    )
    saved_map = map_repo.save(root_map)
    assert saved_map.id == root_map.id

    # 2. Busca por ID
    fetched = map_repo.get_by_id(root_map.id)
    assert fetched is not None
    assert fetched.title == "Engenharia de Software"
    assert fetched.is_public is True

    # 3. Lista por dono
    maps = map_repo.list_by_owner(user.id)
    assert len(maps) == 1
    assert maps[0].id == root_map.id

    # 4. Atualiza mapa
    root_map.title = "Engenharia de Software Avançada"
    map_repo.save(root_map)
    updated = map_repo.get_by_id(root_map.id)
    assert updated is not None
    assert updated.title == "Engenharia de Software Avançada"

    # 5. Remove mapa
    map_repo.delete(root_map.id)
    assert map_repo.get_by_id(root_map.id) is None


@pytest.mark.integration
def test_study_node_and_edge_repository(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)

    user = User(google_sub="sub-tree-2", email="tree2@test.com", name="Graph Architect")
    user_repo.save(user)

    s_map = map_repo.save(StudyMap(owner_id=user.id, title="Algoritmos"))

    # Cria nós
    node_a = node_repo.save(
        StudyNode(map_id=s_map.id, title="Grafos", pos_x=50.0, pos_y=100.0, icon="brain")
    )
    node_b = node_repo.save(
        StudyNode(map_id=s_map.id, title="Árvores AVL", pos_x=200.0, pos_y=100.0, icon="tree")
    )

    nodes = node_repo.list_by_map(s_map.id)
    assert len(nodes) == 2

    # Atualização em lote de coordenadas
    node_repo.update_positions_batch([(node_a.id, 75.0, 150.0), (node_b.id, 250.0, 150.0)])
    updated_a = node_repo.get_by_id(node_a.id)
    assert updated_a is not None
    assert updated_a.pos_x == 75.0
    assert updated_a.pos_y == 150.0

    # Cria aresta A -> B
    edge = edge_repo.save(
        StudyEdge(map_id=s_map.id, source_node_id=node_a.id, target_node_id=node_b.id)
    )
    edges = edge_repo.list_by_map(s_map.id)
    assert len(edges) == 1
    assert edges[0].source_node_id == node_a.id
    assert edges[0].target_node_id == node_b.id

    # Deleta aresta
    edge_repo.delete(edge.id)
    assert edge_repo.get_by_id(edge.id) is None


@pytest.mark.integration
def test_node_content_attachment(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    k_repo = SqlAlchemyKnowledgeSourceRepository(db_session)
    f_repo = SqlAlchemyFlashcardRepository(db_session)

    user = User(google_sub="sub-tree-3", email="tree3@test.com", name="Content Master")
    user_repo.save(user)
    subj = Subject(name="Banco de Dados", owner_id=user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="SQL")
    top_repo.save(topic)

    s_map = map_repo.save(StudyMap(owner_id=user.id, title="DB Map"))
    node = node_repo.save(StudyNode(map_id=s_map.id, title="Indexação"))

    # Cria e vincula pergunta
    q = Question(topic_id=topic.id, prompt="O que é B-Tree?", expected_answer="Árvore balanceada")
    q_repo.save(q)
    content_repo.attach_question(node.id, q.id)

    # Cria e vincula material
    mat = KnowledgeSource(topic_id=topic.id, title="Manual PostgreSQL", content_type="PDF")
    k_repo.save(mat)
    content_repo.attach_knowledge_source(node.id, mat.id)

    # Cria e vincula flashcard
    fc = Flashcard(front="Chave Primária", back="Identificador único", topic_id=topic.id)
    f_repo.save(fc)
    content_repo.attach_flashcard(node.id, fc.id)

    # Verifica vinculações
    mats, ques, flashs = content_repo.get_attached_ids(node.id)
    assert mat.id in mats
    assert q.id in ques
    assert fc.id in flashs

    # Desvincula pergunta, material e flashcard
    content_repo.detach_question(node.id, q.id)
    content_repo.detach_knowledge_source(node.id, mat.id)
    content_repo.detach_flashcard(node.id, fc.id)
    mats_after, ques_after, flashs_after = content_repo.get_attached_ids(node.id)
    assert q.id not in ques_after
    assert mat.id not in mats_after
    assert fc.id not in flashs_after

    # Atualiza nó existente
    node.title = "Indexação Avançada"
    node.description = "B-Tree e Hash"
    updated_node = node_repo.save(node)
    assert updated_node.title == "Indexação Avançada"

    # Deleta nó
    node_repo.delete(node.id)
    assert node_repo.get_by_id(node.id) is None

    # Deleta aresta inexistente e busca inexistente
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)
    edge_repo.delete(uuid4())
    assert edge_repo.get_by_id(uuid4()) is None

    # Testa get_by_questions vazio
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)
    assert prog_repo.get_by_questions(user.id, []) == {}


@pytest.mark.integration
def test_rpg_grimoire_repository_direct_bindings(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    k_repo = SqlAlchemyKnowledgeSourceRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)

    user = User(google_sub="sub-grimoire-1", email="grimoire1@test.com", name="Grimoire Mage")
    user_repo.save(user)
    s_map = map_repo.save(StudyMap(owner_id=user.id, title="Álgebra Abstrata"))

    # 1. StudyNode with theory_content
    node = StudyNode(
        map_id=s_map.id,
        title="Teoria dos Grupos",
        theory_content="Um grupo (G, *) satisfaz fechamento, associatividade, elemento neutro e inverso.",
    )
    saved_node = node_repo.save(node)
    assert (
        saved_node.theory_content
        == "Um grupo (G, *) satisfaz fechamento, associatividade, elemento neutro e inverso."
    )

    fetched_node = node_repo.get_by_id(node.id)
    assert fetched_node is not None
    assert fetched_node.theory_content == saved_node.theory_content

    # Update theory_content
    node.update_theory("Teoria dos Grupos de Lie e álgebras associadas.")
    node_repo.save(node)
    refetched_node = node_repo.get_by_id(node.id)
    assert refetched_node is not None
    assert refetched_node.theory_content == "Teoria dos Grupos de Lie e álgebras associadas."

    # 2. Question with direct node_id (no legacy Topic created in database)
    q_direct = Question(
        prompt="O que é o teorema de Lagrange para grupos finitos?",
        expected_answer="A ordem de um subgrupo divide a ordem do grupo.",
        node_id=node.id,
    )
    q_repo.save(q_direct)

    fetched_q = q_repo.get_by_id(q_direct.id)
    assert fetched_q is not None
    assert fetched_q.node_id == node.id
    assert fetched_q.prompt == q_direct.prompt

    # Also test Question attached via NodeQuestionModel
    q_attached = Question(
        prompt="O que é um subgrupo normal?",
        expected_answer="Um subgrupo N tal que gNg^-1 = N para todo g em G.",
        node_id=node.id,
    )
    q_repo.save(q_attached)
    content_repo.attach_question(node.id, q_attached.id)

    node_questions = q_repo.list_by_node(node.id)
    node_question_ids = {q.id for q in node_questions}
    assert q_direct.id in node_question_ids
    assert q_attached.id in node_question_ids

    # 3. KnowledgeSource with direct node_id and raw_text (no legacy Topic created)
    src_direct = KnowledgeSource(
        title="Tomo de Homomorfismos",
        node_id=node.id,
        raw_text="Homomorfismos preservam a operação de grupo: f(a*b) = f(a)*f(b).",
        content_type="TEXT",
    )
    k_repo.save(src_direct)

    fetched_src = k_repo.get_by_id(src_direct.id)
    assert fetched_src is not None
    assert fetched_src.node_id == node.id
    assert fetched_src.raw_text == src_direct.raw_text

    # Update KnowledgeSource
    src_direct.raw_text = "Texto atualizado com Primeiro Teorema do Isomorfismo."
    k_repo.save(src_direct)
    refetched_src = k_repo.get_by_id(src_direct.id)
    assert refetched_src is not None
    assert refetched_src.raw_text == "Texto atualizado com Primeiro Teorema do Isomorfismo."

    # KnowledgeSource attached via NodeKnowledgeSourceModel
    src_attached = KnowledgeSource(
        title="Pergaminho dos Isomorfismos",
        node_id=node.id,
        raw_text="G / ker(phi) eh isomorfo a Im(phi).",
        content_type="TEXT",
    )
    k_repo.save(src_attached)
    content_repo.attach_knowledge_source(node.id, src_attached.id)

    node_sources = k_repo.list_by_node(node.id)
    node_source_ids = {s.id for s in node_sources}
    assert src_direct.id in node_source_ids
    assert src_attached.id in node_source_ids
