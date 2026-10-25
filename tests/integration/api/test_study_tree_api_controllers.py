"""Testes de integração e segurança Anti-IDOR para as rotas REST da Árvore de Estudos RPG."""

from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyQuestionRepository,
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import (
    Question,
    StudyMap,
    StudyNode,
    Subject,
    Topic,
    User,
)
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-api-tree-1",
        email="tree.creator@test.com",
        name="Tree Creator",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-api-tree-2",
        email="tree.intruder@test.com",
        name="Tree Intruder",
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
def test_create_and_list_study_maps(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)

    # 1. Cria mapa raiz
    payload = {
        "title": "Ciência de Dados",
        "description": "Trilha RPG completa de Data Science",
        "is_public": False,
    }
    response = client.post("/api/v1/study-maps", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Ciência de Dados"
    assert data["owner_id"] == str(test_user.id)
    map_id = data["id"]

    # 2. Lista mapas
    list_resp = client.get("/api/v1/study-maps")
    assert list_resp.status_code == 200
    maps = list_resp.json()
    assert len(maps) == 1
    assert maps[0]["id"] == map_id


@pytest.mark.integration
def test_node_lifecycle_and_batch_positions(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    user_repo.save(test_user)
    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Algoritmos"))

    # 1. Cria nós
    resp1 = client.post(
        f"/api/v1/study-maps/{s_map.id}/nodes",
        json={"title": "Nó 1", "pos_x": 0.0, "pos_y": 0.0, "icon": "sword"},
    )
    assert resp1.status_code == 201
    node1_id = resp1.json()["id"]

    resp2 = client.post(
        f"/api/v1/study-maps/{s_map.id}/nodes",
        json={"title": "Nó 2", "pos_x": 100.0, "pos_y": 100.0, "icon": "shield"},
    )
    assert resp2.status_code == 201
    node2_id = resp2.json()["id"]

    # 2. Atualiza coordenadas em lote
    batch_payload = {
        "positions": [
            {"node_id": node1_id, "pos_x": 150.0, "pos_y": 250.0},
            {"node_id": node2_id, "pos_x": 350.0, "pos_y": 450.0},
        ]
    }
    batch_resp = client.patch(
        f"/api/v1/study-maps/{s_map.id}/nodes/positions-batch", json=batch_payload
    )
    assert batch_resp.status_code == 204

    # 3. Busca grafo e verifica novas coordenadas
    graph_resp = client.get(f"/api/v1/study-maps/{s_map.id}")
    assert graph_resp.status_code == 200
    graph = graph_resp.json()
    assert len(graph["nodes"]) == 2
    n1 = next(n for n in graph["nodes"] if n["id"] == node1_id)
    assert n1["pos_x"] == 150.0
    assert n1["pos_y"] == 250.0


@pytest.mark.integration
def test_edge_connection_and_cycle_rejection(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    user_repo.save(test_user)

    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Grafo RPG"))
    n1 = node_repo.save(StudyNode(map_id=s_map.id, title="A"))
    n2 = node_repo.save(StudyNode(map_id=s_map.id, title="B"))

    # Conecta A -> B
    conn_resp = client.post(
        f"/api/v1/study-maps/{s_map.id}/edges",
        json={"source_node_id": str(n1.id), "target_node_id": str(n2.id)},
    )
    assert conn_resp.status_code == 201
    edge_id = conn_resp.json()["id"]

    # Tentativa de conectar B -> A (ciclo!) deve retornar 400 Bad Request
    cycle_resp = client.post(
        f"/api/v1/study-maps/{s_map.id}/edges",
        json={"source_node_id": str(n2.id), "target_node_id": str(n1.id)},
    )
    assert cycle_resp.status_code == 400
    assert "cíclica" in cycle_resp.json()["detail"].lower()

    # Deleta aresta
    del_resp = client.delete(f"/api/v1/study-maps/{s_map.id}/edges/{edge_id}")
    assert del_resp.status_code == 204


@pytest.mark.integration
def test_attach_and_detach_content_and_study_hub(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Segurança", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Criptografia")
    top_repo.save(topic)
    q = Question(
        topic_id=topic.id,
        prompt="O que é cifra assimétrica?",
        expected_answer="Chaves pública e privada",
    )
    q_repo.save(q)

    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Cyber Security"))
    node = node_repo.save(StudyNode(map_id=s_map.id, title="Cripto Básica"))

    # Vincula pergunta
    attach_resp = client.post(
        f"/api/v1/study-maps/{s_map.id}/nodes/{node.id}/contents",
        json={"content_type": "question", "content_id": str(q.id)},
    )
    assert attach_resp.status_code == 204

    # Busca Hub do Nó
    hub_resp = client.get(f"/api/v1/study-maps/{s_map.id}/nodes/{node.id}/hub")
    assert hub_resp.status_code == 200
    hub_data = hub_resp.json()
    assert len(hub_data["all_questions"]) == 1
    assert hub_data["all_questions"][0]["id"] == str(q.id)

    # Desvincula pergunta
    detach_resp = client.delete(
        f"/api/v1/study-maps/{s_map.id}/nodes/{node.id}/contents/question/{q.id}"
    )
    assert detach_resp.status_code == 204


@pytest.mark.security
def test_idor_protection_rejects_unauthorized_user(
    client: TestClient, db_session: Session, test_user: User, other_user: User
) -> None:
    """Garante que Usuário B não consiga ler nem alterar mapas privados do Usuário A (Anti-IDOR)."""
    user_repo = SqlAlchemyUserRepository(db_session)
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    user_repo.save(test_user)
    user_repo.save(other_user)

    # Mapa privado do test_user
    private_map = map_repo.save(
        StudyMap(owner_id=test_user.id, title="Mapa Ultrassecreto", is_public=False)
    )

    # Força a autenticação como other_user
    app.dependency_overrides[get_current_user] = lambda: other_user

    # Tentativa de acessar o grafo -> 403 Forbidden
    get_resp = client.get(f"/api/v1/study-maps/{private_map.id}")
    assert get_resp.status_code == 403

    # Tentativa de deletar o mapa -> 403 Forbidden
    del_resp = client.delete(f"/api/v1/study-maps/{private_map.id}")
    assert del_resp.status_code == 403

    # Tentativa de criar nó no mapa alheio -> 403 Forbidden
    post_node_resp = client.post(
        f"/api/v1/study-maps/{private_map.id}/nodes",
        json={"title": "Nó Invasor"},
    )
    assert post_node_resp.status_code == 403
