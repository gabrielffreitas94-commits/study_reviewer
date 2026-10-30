"""Testes de integração e contratos para o Canvas Unificado em Modo Forja,

Right-Click no nodes-layer e envio de respostas/feedback no Grimoire.
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
        google_sub="sub-canvas-unified-tester",
        email="canvas.unified.tester@test.com",
        name="Artífice da Forja Unificada",
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
def test_canvas_template_unified_forge_mode(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Valida se o canvas.html renderiza a HUD da Forja Unificada com editor-actions visivel."""
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    study_map = StudyMap(
        owner_id=test_user.id,
        title="Trilha do Mestre Forjador",
        description="Canvas Unificado em Modo Forja",
    )
    map_repo.save(study_map)

    res = client.get(f"/study-maps/{study_map.id}/canvas")
    assert res.status_code == 200
    html = res.text

    # Toolbar unificada exibe Forja Ancestral e ações sempre disponíveis
    assert "Forja Ancestral" in html
    assert 'id="editor-actions"' in html
    # editor-actions não deve ter a classe hidden no HTML inicial
    assert 'id="editor-actions" class="hidden' not in html

    # IDs e rótulos de compatibilidade legada preservados no DOM (hidden)
    assert 'id="btn-mode-study"' in html
    assert 'id="btn-mode-edit"' in html
    assert "Modo Jornada" in html
    assert "Modo Forja" in html


@pytest.mark.integration
def test_study_canvas_js_unified_forge_and_nodes_layer_pan() -> None:
    """Valida contratos do study_canvas.js para modo forge padrao e pan/right-click no nodes-layer."""
    js_path = Path("src/adapters/web/static/js/study_canvas.js")
    assert js_path.exists(), "study_canvas.js deve existir!"
    content = js_path.read_text(encoding="utf-8")

    # 1. Modo Forja ativo por padrão
    assert "interactionMode: 'forge'" in content

    # 2. Reconhecimento do nodes-layer como background para mousedown e contextmenu
    assert "nodes-layer" in content
    assert "e.target.id === 'nodes-layer'" in content
    assert "e.button === 0 || e.button === 1" in content

    # 3. Inicialização e compatibilidade de API pública
    assert "initCanvas" in content
    assert "window.initCanvas = initCanvas" in content
    assert "window.setCanvasMode" in content
    assert "window.setupViewportEvents" in content


@pytest.mark.integration
def test_node_grimoire_dificil_button_and_review_wiring(client: TestClient) -> None:
    """Valida se o node_grimoire.html envia 25% para Dificil e inclui campos semanticos de IA."""
    sample_res = client.post("/api/v1/study-maps/sample-math")
    assert sample_res.status_code == 201
    map_id = sample_res.json()["id"]

    graph_res = client.get(f"/api/v1/study-maps/{map_id}")
    assert graph_res.status_code == 200
    nodes = graph_res.json()["nodes"]
    assert len(nodes) > 0
    node_id = nodes[0]["id"]

    res = client.get(f"/study-maps/{map_id}/nodes/{node_id}")
    assert res.status_code == 200
    html = res.text

    # 1. Botão Difícil calibrado para 25%
    assert "Difícil (25%)" in html
    assert "submitNodeReview(null, 'hard', 25)" in html

    # 2. Função submitNodeReview deve empacotar student_answer, ai_feedback e evaluation_mode
    assert "student_answer" in html
    assert "ai_feedback" in html
    assert "evaluation_mode" in html
    assert "conjure-textarea" in html
    assert "conjure-feedback" in html
