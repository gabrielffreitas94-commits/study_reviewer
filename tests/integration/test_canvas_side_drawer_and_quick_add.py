"""Testes de integração para o 1-Click Connected Child Node e Side Drawer Interativo no Canvas.

Valida:
1. Marcação estrutural no canvas.html (#node-side-drawer, #quick-child-modal, campos de teoria e lote).
2. Contratos de funções e endpoints no study_canvas.js.
3. Fluxo de criação de nó filho conectado via API REST (nodes + edges).
4. Fluxo de atualização de teoria e importação de questões em lote via API REST (/theory e /questions/batch).
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyStudyMapRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import StudyMap, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-canvas-side-drawer-tester",
        email="side.drawer.tester@test.com",
        name="Artífice do Canvas",
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
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)

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
def test_canvas_template_has_side_drawer_and_quick_child_markup(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Valida se o canvas.html renderiza #node-side-drawer, #quick-child-modal e seus componentes."""
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    study_map = StudyMap(
        owner_id=test_user.id,
        title="Árvore de Engenharia de Software",
        description="Estudo com IA e Grafo de Habilidades",
    )
    map_repo.save(study_map)

    res = client.get(f"/study-maps/{study_map.id}/canvas")
    assert res.status_code == 200
    html = res.text

    # 1. Slide-Over Side Drawer
    assert 'id="node-side-drawer"' in html
    assert 'id="drawer-node-title"' in html
    assert 'id="drawer-node-rank"' in html
    assert 'id="drawer-theory-input"' in html
    assert "saveDrawerTheory" in html
    assert 'id="drawer-theory-status"' in html
    assert 'id="drawer-bulk-questions-input"' in html
    assert "submitDrawerBulkQuestions" in html
    assert 'id="drawer-questions-list"' in html
    assert 'id="drawer-prerequisites-list"' in html
    assert "openSelectedNodeGrimoire" in html
    assert "closeNodeSideDrawer" in html

    # 2. Modal de 1-Click Quick Add Child
    assert 'id="quick-child-modal"' in html
    assert 'id="quick-child-form"' in html
    assert 'id="quick-child-title-input"' in html
    assert "handleQuickChildSubmit" in html
    assert "closeQuickChildModal" in html

    # 3. Contratos de ausência de IDs legados
    assert 'id="node-drawer"' not in html
    assert 'id="attach-modal"' not in html
    assert "Vincular da Biblioteca" not in html


@pytest.mark.integration
def test_study_canvas_js_side_drawer_and_quick_add_contracts() -> None:
    """Valida a presença das funções exigidas de Quick Add e Side Drawer no study_canvas.js."""
    js_path = Path("src/adapters/web/static/js/study_canvas.js")
    assert js_path.exists(), "study_canvas.js deve existir!"
    content = js_path.read_text(encoding="utf-8")

    # Funções do Quick Add Child
    assert "quickAddChildNode" in content
    assert "quick-add-child-btn" in content
    assert "handleQuickChildSubmit" in content

    # Funções do Side Drawer
    assert "openNodeSideDrawer" in content
    assert "closeNodeSideDrawer" in content
    assert "saveDrawerTheory" in content
    assert "submitDrawerBulkQuestions" in content
    assert "switchDrawerTab" in content
    assert "parseBulkQuestions" in content

    # Endpoints REST invocados
    assert "/questions/batch" in content
    assert "/theory" in content
    assert "/edges" in content
    assert "/study-maps/" in content
    assert "/nodes/" in content


@pytest.mark.integration
def test_quick_add_child_api_workflow(client: TestClient) -> None:
    """Valida o fluxo de API correspondente ao Quick Add: criação do nó e aresta de conexão."""
    map_res = client.post(
        "/api/v1/study-maps",
        json={"title": "Grafo de Arquitetura", "description": "Quick Add Test"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    # Cria nó pai
    p_res = client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={"title": "Design Patterns", "pos_x": 100, "pos_y": 100, "icon": "brain"},
    )
    assert p_res.status_code == 201
    parent_node = p_res.json()

    # Cria nó filho
    c_res = client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={
            "title": "Strategy Pattern",
            "pos_x": parent_node["pos_x"] + 200,
            "pos_y": parent_node["pos_y"],
            "icon": "brain",
        },
    )
    assert c_res.status_code == 201
    child_node = c_res.json()

    # Conecta aresta
    edge_res = client.post(
        f"/api/v1/study-maps/{map_id}/edges",
        json={
            "source_node_id": parent_node["id"],
            "target_node_id": child_node["id"],
            "required_level": 1,
        },
    )
    assert edge_res.status_code == 201

    # Verifica grafo completo
    graph_res = client.get(f"/api/v1/study-maps/{map_id}")
    assert graph_res.status_code == 200
    graph = graph_res.json()
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["source_node_id"] == parent_node["id"]
    assert graph["edges"][0]["target_node_id"] == child_node["id"]


@pytest.mark.integration
def test_side_drawer_theory_and_batch_questions_api_workflow(client: TestClient) -> None:
    """Valida os endpoints REST consumidos pelo Side Drawer: salvar resumo e importar lote."""
    map_res = client.post(
        "/api/v1/study-maps",
        json={"title": "Grafo com Drawer", "description": "Teste de Teoria e Lote"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    node_res = client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={"title": "SOLID Principles", "pos_x": 200, "pos_y": 200, "icon": "code"},
    )
    assert node_res.status_code == 201
    node_id = node_res.json()["id"]

    # 1. Salvar Resumo (Theory)
    theory_text = "O princípio Aberto-Fechado (OCP) diz que entidades devem ser abertas para extensão e fechadas para modificação."
    put_res = client.patch(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/theory",
        json={"theory_content": theory_text},
    )
    assert put_res.status_code == 200

    # 2. Importar Questões em Lote (Batch Questions)
    batch_res = client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/batch",
        json={
            "questions": [
                {
                    "prompt": "O que significa a letra 'S' em SOLID?",
                    "expected_answer": "Single Responsibility Principle (Princípio da Responsabilidade Única).",
                },
                {
                    "prompt": "O que preconiza o princípio Liskov Substitution?",
                    "expected_answer": "Subtipos devem ser substituíveis pelos seus tipos base sem quebrar o sistema.",
                },
            ]
        },
    )
    assert batch_res.status_code == 201
    created_questions = batch_res.json()
    assert len(created_questions) == 2

    # 3. Consulta ao Hub do Nó (o que o Side Drawer carrega)
    hub_res = client.get(f"/api/v1/study-maps/{map_id}/nodes/{node_id}/hub")
    assert hub_res.status_code == 200
    hub_data = hub_res.json()
    assert hub_data["node"]["theory_content"] == theory_text
    assert len(hub_data["all_questions"]) == 2

    # 4. Excluir uma questão pelo Side Drawer
    q_to_delete = created_questions[0]["id"]
    del_res = client.delete(f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{q_to_delete}")
    assert del_res.status_code == 204

    # Verifica se restou apenas 1 questão no hub
    hub_after = client.get(f"/api/v1/study-maps/{map_id}/nodes/{node_id}/hub").json()
    assert len(hub_after["all_questions"]) == 1
