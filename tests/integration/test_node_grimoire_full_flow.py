"""Testes de integração end-to-end do Grimório Dedicado do Nó (node_grimoire.html)
e estilização RPG das Provações Diárias e Crônicas.
"""

from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import SqlAlchemyUserRepository
from src.domain.entities import User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-grimoire-fullflow",
        email="grimoire.fullflow@test.com",
        name="Mago das Equações",
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
def authenticated_client(db_session: Session, test_user: User) -> Generator[TestClient]:
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
def test_sample_math_tree_to_node_grimoire_end_to_end(authenticated_client: TestClient) -> None:
    """Valida o fluxo completo da criação da árvore modelo até a arena interativa do Grimório."""
    # 1. Cria Árvore Modelo de Matemática Aplicada
    sample_res = authenticated_client.post("/api/v1/study-maps/sample-math")
    assert sample_res.status_code == 201
    map_id = sample_res.json()["id"]

    # 2. Busca grafo e valida os 5 nós ricos em teoria
    graph_res = authenticated_client.get(f"/api/v1/study-maps/{map_id}")
    assert graph_res.status_code == 200
    nodes = graph_res.json()["nodes"]
    assert len(nodes) == 5
    for node in nodes:
        assert node["theory_content"], f"Nó {node['title']} deve ter conteúdo teórico rico"
        assert len(node["theory_content"]) > 40

    # 3. Abre a página dedicada do primeiro nó (Álgebra Linear Computacional)
    root_node = next(n for n in nodes if "Álgebra Linear" in n["title"])
    node_id = root_node["id"]
    page_res = authenticated_client.get(f"/study-maps/{map_id}/nodes/{node_id}")
    assert page_res.status_code == 200
    html = page_res.text

    # Breadcrumb para o Canvas
    assert f"/study-maps/{map_id}/canvas" in html
    assert ("Voltar à Árvore" in html or "Retornar à Árvore" in html)

    # Coluna Esquerda: Tomo de Sabedoria com Cormorant Garamond, editor e materiais
    assert "Tomo de Sabedoria" in html
    assert "font-tome" in html
    assert 'id="theory-editor"' in html
    assert "saveNodeTheory" in html
    assert 'id="new-material-form"' in html
    assert "createNodeMaterial" in html

    # Coluna Direita: Provações de Maestria com SRS Arena, modos e forja de perguntas
    assert "Provações de Maestria" in html
    assert "Revelar Runas" in html
    assert "Conjurar Resposta" in html
    assert "Voz Arcana" in html
    assert "submitNodeReview" in html
    assert "Modo Treino Livre" in html
    assert "Forjar Nova Provação" in html
    assert 'id="new-question-form"' in html
    assert "createNodeQuestion" in html

    # 4. Obtém as perguntas do nó pelo Hub e revisa todas com nota 100
    hub_res = authenticated_client.get(f"/api/v1/study-maps/{map_id}/nodes/{node_id}/study-hub")
    assert hub_res.status_code == 200
    questions = hub_res.json()["all_questions"]
    assert len(questions) >= 3

    last_rev_data = None
    for q in questions:
        qid = q["id"]
        rev_res = authenticated_client.post(
            f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{qid}/review",
            json={"score": 100},
        )
        assert rev_res.status_code == 200
        last_rev_data = rev_res.json()

    assert last_rev_data is not None
    assert last_rev_data["new_node_level"] >= 1
    assert last_rev_data["node_effective_level"] >= 1
    # Verifica que nós dependentes foram destrancados
    unlocked = last_rev_data.get("unlocked_node_ids", [])
    assert len(unlocked) >= 1

    # 5. Modo Treino Livre: revisa novamente no mesmo dia
    first_qid = questions[0]["id"]
    free_rev_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{first_qid}/review",
        json={"score": 100},
    )
    assert free_rev_res.status_code == 200
    free_data = free_rev_res.json()
    assert free_data["is_training_only"] is True


@pytest.mark.integration
def test_daily_trials_and_performance_hub_render_rpg_theme(authenticated_client: TestClient) -> None:
    """Verifica que Provações Diárias e Crônicas renderizam com estilo RPG Grimoire."""
    # 1. Provações Diárias (/questions/study)
    study_res = authenticated_client.get("/questions/study")
    assert study_res.status_code == 200
    study_html = study_res.text
    assert "font-cinzel" in study_html
    assert "rpg-panel" in study_html
    assert "Provações Diárias" in study_html

    # 2. Crônicas & Atributos (/performance)
    perf_res = authenticated_client.get("/performance")
    assert perf_res.status_code == 200
    perf_html = perf_res.text
    assert "font-cinzel" in perf_html
    assert "rpg-panel" in perf_html
    assert "Crônicas & Atributos" in perf_html
