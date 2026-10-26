"""Testes de integração para as rotas REST de Arestas de Estudo e Calibração de Nível Requerido (RPG)."""

from collections.abc import Generator
from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
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
    Question,
    StudyEdge,
    StudyMap,
    StudyNode,
    Subject,
    Topic,
    User,
    UserQuestionProgress,
)
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-rpg-edge-owner",
        email="edge.owner@test.com",
        name="Edge Master",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-rpg-edge-intruder",
        email="edge.intruder@test.com",
        name="Edge Intruder",
    )


@pytest.fixture
def db_engine() -> Generator[Any]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Any) -> Generator[Session]:
    testing_session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session, test_user: User) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db_session

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.integration
def test_create_edge_with_custom_required_level(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)

    user_repo.save(test_user)
    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Mapa Arestas"))
    node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Nó A"))
    node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Nó B"))

    # Criar aresta com required_level = 3
    resp = client.post(
        f"/api/v1/study-maps/{s_map.id}/edges",
        json={
            "source_node_id": str(node_a.id),
            "target_node_id": str(node_b.id),
            "required_level": 3,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_node_id"] == str(node_a.id)
    assert data["target_node_id"] == str(node_b.id)
    assert data["required_level"] == 3

    # Verifica persistência no banco
    edges = edge_repo.list_by_map(s_map.id)
    assert len(edges) == 1
    assert edges[0].required_level == 3


@pytest.mark.integration
def test_create_edge_default_required_level(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)

    user_repo.save(test_user)
    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Mapa Default Edge"))
    node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Nó A"))
    node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Nó B"))

    # Criação sem informar required_level -> default 1
    resp = client.post(
        f"/api/v1/study-maps/{s_map.id}/edges",
        json={
            "source_node_id": str(node_a.id),
            "target_node_id": str(node_b.id),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["required_level"] == 1

    edges = edge_repo.list_by_map(s_map.id)
    assert len(edges) == 1
    assert edges[0].required_level == 1


@pytest.mark.integration
def test_update_edge_required_level_success(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)

    user_repo.save(test_user)
    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Mapa Update Edge"))
    node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Nó A"))
    node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Nó B"))
    edge = edge_repo.save(
        StudyEdge(
            map_id=s_map.id,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
            required_level=1,
        )
    )

    # PATCH /api/v1/study-maps/{map_id}/edges/{edge_id} -> required_level = 2
    resp = client.patch(
        f"/api/v1/study-maps/{s_map.id}/edges/{edge.id}",
        json={"required_level": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(edge.id)
    assert data["required_level"] == 2

    # Verifica persistência
    reloaded = edge_repo.get_by_id(edge.id)
    assert reloaded is not None
    assert reloaded.required_level == 2


@pytest.mark.integration
def test_update_edge_unauthorized_user_forbidden(
    client: TestClient, db_session: Session, test_user: User, other_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)

    user_repo.save(test_user)
    user_repo.save(other_user)
    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Mapa Privado"))
    node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Nó A"))
    node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Nó B"))
    edge = edge_repo.save(
        StudyEdge(
            map_id=s_map.id,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
            required_level=1,
        )
    )

    # Invasor tenta atualizar
    app.dependency_overrides[get_current_user] = lambda: other_user

    resp = client.patch(
        f"/api/v1/study-maps/{s_map.id}/edges/{edge.id}",
        json={"required_level": 4},
    )
    assert resp.status_code == 403


@pytest.mark.integration
def test_update_edge_not_found(client: TestClient, db_session: Session, test_user: User) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)

    user_repo.save(test_user)
    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Mapa Not Found"))
    node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Nó A"))
    node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Nó B"))
    edge = edge_repo.save(
        StudyEdge(
            map_id=s_map.id,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
            required_level=1,
        )
    )

    # Mapa inexistente -> 404
    fake_map_id = uuid4()
    resp_fake_map = client.patch(
        f"/api/v1/study-maps/{fake_map_id}/edges/{edge.id}",
        json={"required_level": 2},
    )
    assert resp_fake_map.status_code == 404

    # Aresta inexistente -> 404
    fake_edge_id = uuid4()
    resp_fake_edge = client.patch(
        f"/api/v1/study-maps/{s_map.id}/edges/{fake_edge_id}",
        json={"required_level": 2},
    )
    assert resp_fake_edge.status_code == 404

    # Aresta de outro mapa -> 404
    other_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Outro Mapa"))
    resp_wrong_map = client.patch(
        f"/api/v1/study-maps/{other_map.id}/edges/{edge.id}",
        json={"required_level": 2},
    )
    assert resp_wrong_map.status_code == 404


@pytest.mark.integration
def test_update_edge_validation_limits(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)

    user_repo.save(test_user)
    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Mapa Limits"))
    node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Nó A"))
    node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Nó B"))
    edge = edge_repo.save(
        StudyEdge(
            map_id=s_map.id,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
            required_level=1,
        )
    )

    # required_level < 1 -> 422
    resp_low = client.patch(
        f"/api/v1/study-maps/{s_map.id}/edges/{edge.id}",
        json={"required_level": 0},
    )
    assert resp_low.status_code == 422

    # required_level > 6 -> 422
    resp_high = client.patch(
        f"/api/v1/study-maps/{s_map.id}/edges/{edge.id}",
        json={"required_level": 7},
    )
    assert resp_high.status_code == 422


@pytest.mark.integration
def test_update_edge_domain_validation_error(
    client: TestClient,
    db_session: Session,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.application.use_cases.study_tree_use_cases import UpdateStudyEdgeUseCase
    from src.domain.exceptions import DomainValidationError

    def mock_execute(*args: Any, **kwargs: Any) -> Any:
        raise DomainValidationError("Nível requerido fora do intervalo permitido.")

    monkeypatch.setattr(UpdateStudyEdgeUseCase, "execute", mock_execute)

    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    user_repo.save(test_user)
    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Mapa Domain Error"))

    resp = client.patch(
        f"/api/v1/study-maps/{s_map.id}/edges/{uuid4()}",
        json={"required_level": 3},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Nível requerido fora do intervalo permitido."


@pytest.mark.integration
def test_get_study_map_graph_includes_required_level(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)

    user_repo.save(test_user)
    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Grafo com Níveis"))
    node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Nó A"))
    node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Nó B"))
    edge = edge_repo.save(
        StudyEdge(
            map_id=s_map.id,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
            required_level=4,
        )
    )

    resp = client.get(f"/api/v1/study-maps/{s_map.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["edges"]) == 1
    edge_data = data["edges"][0]
    assert edge_data["id"] == str(edge.id)
    assert edge_data["required_level"] == 4


@pytest.mark.integration
def test_multi_prerequisite_unlocking_progression(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    topic_repo = SqlAlchemyTopicRepository(db_session)
    question_repo = SqlAlchemyQuestionRepository(db_session)
    progress_repo = SqlAlchemyQuestionProgressRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Ciência Mágica", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Conduítes Rúnicos")
    topic_repo.save(topic)

    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Árvore Complexa"))
    node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Nó A"))
    node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Nó B"))
    node_c = node_repo.save(StudyNode(map_id=s_map.id, title="Nó C"))

    # Node C requer Node A (req=3) e Node B (req=1)
    edge_repo.save(
        StudyEdge(
            map_id=s_map.id,
            source_node_id=node_a.id,
            target_node_id=node_c.id,
            required_level=3,
        )
    )
    edge_repo.save(
        StudyEdge(
            map_id=s_map.id,
            source_node_id=node_b.id,
            target_node_id=node_c.id,
            required_level=1,
        )
    )

    # Pergunta para Node A
    q_a = Question(topic_id=topic.id, prompt="Pergunta A?", expected_answer="Resp A")
    question_repo.save(q_a)
    content_repo.attach_question(node_a.id, q_a.id)

    # Pergunta para Node B
    q_b = Question(topic_id=topic.id, prompt="Pergunta B?", expected_answer="Resp B")
    question_repo.save(q_b)
    content_repo.attach_question(node_b.id, q_b.id)

    # Inicialmente: Node A nível 1, Node B nível 1
    prog_a = UserQuestionProgress(
        user_id=test_user.id,
        question_id=q_a.id,
        current_level=1,
        next_review_date=date.today(),
    )
    progress_repo.save(prog_a)

    prog_b = UserQuestionProgress(
        user_id=test_user.id,
        question_id=q_b.id,
        current_level=1,
        next_review_date=date.today(),
    )
    progress_repo.save(prog_b)

    # Consulta grafo: Node C deve estar bloqueado (is_unlocked: False) pois A tem nível 1 < req 3
    resp1 = client.get(f"/api/v1/study-maps/{s_map.id}")
    assert resp1.status_code == 200
    nodes1 = {n["id"]: n for n in resp1.json()["nodes"]}
    assert nodes1[str(node_a.id)]["effective_level"] == 1
    assert nodes1[str(node_b.id)]["effective_level"] == 1
    assert nodes1[str(node_c.id)]["is_unlocked"] is False

    # Estudante avança Node A para nível 3
    prog_a.current_level = 3
    progress_repo.save(prog_a)

    # Consulta grafo novamente: Node C agora deve estar desbloqueado (is_unlocked: True)
    resp2 = client.get(f"/api/v1/study-maps/{s_map.id}")
    assert resp2.status_code == 200
    nodes2 = {n["id"]: n for n in resp2.json()["nodes"]}
    assert nodes2[str(node_a.id)]["effective_level"] == 3
    assert nodes2[str(node_b.id)]["effective_level"] == 1
    assert nodes2[str(node_c.id)]["is_unlocked"] is True
