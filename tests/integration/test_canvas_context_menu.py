"""Testes de integração para os Menus de Contexto (Right-Click RPG) no Canvas.

Valida:
1. Marcação estrutural no canvas.html (#node-context-menu, #canvas-context-menu e botões de ação).
2. Contratos de funções e listeners de evento contextmenu no study_canvas.js.
3. Fluxo de API para criação de nós posicionados via coordenadas do cursor.
4. Preservação de contratos arquiteturais (ausência de IDs legados, ordem renderEdges/renderNodes).
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
        google_sub="sub-canvas-context-menu-tester",
        email="context.menu.tester@test.com",
        name="Mestre da Forja de Grafos",
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
def test_canvas_template_has_context_menus_markup(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Valida se o canvas.html renderiza #node-context-menu, #canvas-context-menu e todas as 8 ações."""
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    study_map = StudyMap(
        owner_id=test_user.id,
        title="Árvore de Estruturas de Dados Avançadas",
        description="Teste de Menu de Contexto RPG",
    )
    map_repo.save(study_map)

    res = client.get(f"/study-maps/{study_map.id}/canvas")
    assert res.status_code == 200
    html = res.text

    # 1. Menu de Contexto do Nó
    assert 'id="node-context-menu"' in html
    assert 'id="ctx-node-icon"' in html
    assert 'id="ctx-node-title"' in html

    # Grupo 1: Expansão & Conexão
    assert 'id="ctx-btn-create-child"' in html
    assert "ctxCreateChildNode()" in html
    assert "Criar Nó Filho Conectado" in html

    assert 'id="ctx-btn-start-connection"' in html
    assert "ctxStartConnection()" in html
    assert "Puxar Conexão (Pré-requisito)" in html

    # Grupo 2: Alimentar com IA
    assert 'id="ctx-btn-open-theory"' in html
    assert "ctxOpenTheory()" in html
    assert "Colar Resumo / Teoria" in html

    assert 'id="ctx-btn-open-bulk-questions"' in html
    assert "ctxOpenBulkQuestions()" in html
    assert "Colar Questões em Lote" in html

    # Grupo 3: Estudo
    assert 'id="ctx-btn-study-node"' in html
    assert "ctxStudyNode()" in html
    assert "Estudar este Nó (Tela Cheia)" in html

    # Grupo 4: Manutenção
    assert 'id="ctx-btn-edit-meta"' in html
    assert "ctxEditNodeMeta()" in html
    assert "Renomear / Trocar Ícone" in html

    assert 'id="ctx-btn-delete-node"' in html
    assert "ctxDeleteNode()" in html
    assert "Excluir Nó" in html

    # 2. Menu de Contexto do Fundo do Mapa (Canvas)
    assert 'id="canvas-context-menu"' in html
    assert 'id="ctx-btn-create-node-here"' in html
    assert "ctxCreateNodeAtCursor()" in html
    assert "Criar Nó Aqui" in html

    assert 'id="ctx-btn-reset-view"' in html
    assert "resetView()" in html
    assert "Centralizar Câmera" in html

    # 3. Contratos de ausência de IDs legados
    assert 'id="node-drawer"' not in html
    assert 'id="attach-modal"' not in html


@pytest.mark.integration
def test_study_canvas_js_context_menu_contracts() -> None:
    """Valida a presença de listeners e funções de Menu de Contexto no study_canvas.js."""
    js_path = Path("src/adapters/web/static/js/study_canvas.js")
    assert js_path.exists(), "study_canvas.js deve existir!"
    content = js_path.read_text(encoding="utf-8")

    # Listeners de contextmenu registrados
    assert "contextmenu" in content
    assert "onNodeContextMenu" in content
    assert "onCanvasContextMenu" in content
    assert "closeContextMenus" in content

    # Estado global com rastreamento de nó e coordenadas do menu de contexto
    assert "contextMenuNode" in content
    assert "contextMenuWorldPos" in content
    assert "pendingSpawnCoords" in content

    # Funções de ação do menu do nó
    assert "ctxCreateChildNode" in content
    assert "ctxStartConnection" in content
    assert "ctxOpenTheory" in content
    assert "ctxOpenBulkQuestions" in content
    assert "ctxStudyNode" in content
    assert "ctxEditNodeMeta" in content
    assert "ctxDeleteNode" in content

    # Ação de criação de nó no cursor
    assert "ctxCreateNodeAtCursor" in content

    # Exposição no objeto window
    assert "window.closeContextMenus = closeContextMenus" in content
    assert "window.onNodeContextMenu = onNodeContextMenu" in content
    assert "window.onCanvasContextMenu = onCanvasContextMenu" in content
    assert "window.ctxCreateChildNode = ctxCreateChildNode" in content
    assert "window.ctxStartConnection = ctxStartConnection" in content
    assert "window.ctxOpenTheory = ctxOpenTheory" in content
    assert "window.ctxOpenBulkQuestions = ctxOpenBulkQuestions" in content
    assert "window.ctxStudyNode = ctxStudyNode" in content
    assert "window.ctxEditNodeMeta = ctxEditNodeMeta" in content
    assert "window.ctxDeleteNode = ctxDeleteNode" in content
    assert "window.ctxCreateNodeAtCursor = ctxCreateNodeAtCursor" in content

    # Validação da ordem arquitetural: renderEdges antes de renderNodes
    pos_edges = content.find("function renderEdges")
    pos_nodes = content.find("function renderNodes")
    assert pos_edges != -1, "renderEdges deve ser definida"
    assert pos_nodes != -1, "renderNodes deve ser definida"
    assert pos_edges < pos_nodes, "renderEdges deve vir antes de renderNodes"


@pytest.mark.integration
def test_canvas_node_creation_at_cursor_api_flow(client: TestClient) -> None:
    """Valida o fluxo de API correspondente à criação de nó nas coordenadas exatas do cursor."""
    # 1. Cria mapa
    map_res = client.post(
        "/api/v1/study-maps",
        json={"title": "Mapa de Algoritmos", "description": "Teste spawn coordenadas"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    # 2. Cria nó simulando as coordenadas calculadas pelo menu de contexto
    cursor_x = 520
    cursor_y = 380
    node_res = client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={
            "title": "Nó Rúnico no Cursor",
            "description": "Criado via menu de contexto do mapa",
            "icon": "sword",
            "pos_x": cursor_x,
            "pos_y": cursor_y,
        },
    )
    assert node_res.status_code == 201
    node_data = node_res.json()
    assert node_data["title"] == "Nó Rúnico no Cursor"
    assert node_data["pos_x"] == cursor_x
    assert node_data["pos_y"] == cursor_y

    # 3. Verifica se o grafo reflete o nó na posição exata
    graph_res = client.get(f"/api/v1/study-maps/{map_id}")
    assert graph_res.status_code == 200
    nodes = graph_res.json()["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["pos_x"] == cursor_x
    assert nodes[0]["pos_y"] == cursor_y
