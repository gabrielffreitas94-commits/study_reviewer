"""Testes de integração para a Geometria Limpa de Conduítes no Canvas e Inspetor de Pré-requisitos (Modo Forja & Grimório).

Valida:
1. Linhas limpas sem poluição textual ou badges flutuantes.
2. Cálculo geométrico do raio externo (R = 42px) no study_canvas.js para que as linhas não entrem no centro dos medalhões.
3. Inspetor de pré-requisitos no Modo Forja (canvas.html e study_canvas.js) com calibração de nível (1-4) e dissipação.
4. Exibição clara dos requisitos com nível exigido no Grimório do Nó (node_grimoire.html).
"""

from collections.abc import Generator
from datetime import date
from pathlib import Path
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
        google_sub="sub-conduits-tester",
        email="conduits.tester@test.com",
        name="Artífice dos Conduítes",
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
def test_canvas_template_has_prerequisite_inspector_markup(client: TestClient) -> None:
    """Valida se o canvas.html possui a marcação estrutural do Inspetor de Pré-requisitos da Forja."""
    map_res = client.post(
        "/api/v1/study-maps",
        json={"title": "Forja do Éter", "description": "Calibração dos Conduítes"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    canvas_res = client.get(f"/study-maps/{map_id}/canvas")
    assert canvas_res.status_code == 200
    html = canvas_res.text

    # Verifica seção e lista de pré-requisitos
    assert "node-prerequisites-list" in html
    assert "node-prerequisites-section" in html
    assert (
        "Pré-requisitos &amp; Bloqueios do Nó" in html or "Pré-requisitos & Bloqueios do Nó" in html
    )

    # Verifica formulário de adição com seletores de nó e nível
    assert "add-prerequisite-form" in html
    assert "new-prereq-node-select" in html or "add-prerequisite-select" in html
    assert "new-prereq-level-select" in html or "add-prerequisite-level" in html
    assert "+ Conectar Bloqueio" in html

    # Verifica opções de calibração de nível (1 a 4)
    assert 'value="1"' in html
    assert 'value="2"' in html
    assert 'value="3"' in html
    assert 'value="4"' in html

    # Verifica os marcadores de conduítes no SVG <defs>
    assert 'id="arrow-unlocked"' in html
    assert 'id="edge-unlocked-grad"' in html


@pytest.mark.integration
def test_study_canvas_js_implements_clean_outer_boundary_conduits_and_inspector_logic() -> None:
    """Valida a lógica em study_canvas.js: geometria R=42px, linhas limpas sem texto flutuante e APIs de aresta."""
    js_path = Path("src/adapters/web/static/js/study_canvas.js")
    assert js_path.exists(), "study_canvas.js deve existir!"

    content = js_path.read_text(encoding="utf-8")

    # 1. Geometria do conduíte exterior (R = 42px)
    assert "Math.hypot" in content, (
        "study_canvas.js deve calcular distância euclidiana via Math.hypot"
    )
    assert "42" in content, "study_canvas.js deve usar raio externo R=42 para os medalhões de 80px"
    assert "dist > R * 2" in content or "dist > 84" in content or "R * ux" in content, (
        "study_canvas.js deve transladar os pontos inicial e final para a borda externa do medalhão"
    )

    # 2. Curva Bezier cúbica suave
    assert "M ${startX} ${startY}" in content or "M ${sx" in content or "startX" in content

    # 3. Regra de ouro da experiência do usuário: linhas LIMPAS no Canvas (sem rótulos poluindo)
    # Não deve criar elementos <text> ou badges flutuantes em renderEdges
    render_edges_start = content.find("function renderEdges")
    assert render_edges_start != -1
    render_edges_end = content.find("function renderNodes", render_edges_start)
    edges_code = content[render_edges_start:render_edges_end]
    assert "createElementNS('http://www.w3.org/2000/svg', 'text')" not in edges_code, (
        "Canvas lines must remain clean! No floating <text> labels inside renderEdges."
    )

    # 4. Inspetor da Forja: Calibração de nível com PATCH
    assert "updateEdgeRequiredLevel" in content
    assert "PATCH" in content
    assert "/edges/" in content
    assert "required_level" in content

    # 5. Dissipação de vínculo com DELETE
    assert "deleteEdge" in content
    assert "DELETE" in content

    # 6. Adição de novo vínculo com nível
    assert "addPrerequisiteEdge" in content
    assert "POST" in content


@pytest.mark.integration
def test_node_grimoire_displays_detailed_prerequisites_with_required_levels(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Valida a renderização detalhada de pré-requisitos no Grimório do Nó.

    Quando bloqueado: exibe '🔒 Selado — Requer:' com os títulos dos nós e seus respectivos níveis exigidos.
    Quando desbloqueado: exibe '🔓 Selos Arcanos Satisfeitos (Pronto para Estudo)'.
    """
    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    edge_repo = SqlAlchemyStudyEdgeRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)

    s_map = map_repo.save(StudyMap(owner_id=test_user.id, title="Árvore de Grimórios"))
    node_a = node_repo.save(StudyNode(map_id=s_map.id, title="Álgebra Linear"))
    node_b = node_repo.save(StudyNode(map_id=s_map.id, title="Cálculo Diferencial"))
    node_target = node_repo.save(StudyNode(map_id=s_map.id, title="Geometria Riemanniana"))

    # Criar vínculos:
    # Álgebra Linear -> Geometria Riemanniana (requer Nv. 1)
    # Cálculo Diferencial -> Geometria Riemanniana (requer Nv. 3)
    edge_repo.save(
        StudyEdge(
            map_id=s_map.id,
            source_node_id=node_a.id,
            target_node_id=node_target.id,
            required_level=1,
        )
    )
    edge_repo.save(
        StudyEdge(
            map_id=s_map.id,
            source_node_id=node_b.id,
            target_node_id=node_target.id,
            required_level=3,
        )
    )

    # Questões para permitir nível nos nós ancestrais
    subj = Subject(owner_id=test_user.id, name="Matemática Avançada")
    subj_repo.save(subj)
    top = Topic(subject_id=subj.id, name="Tópicos")
    top_repo.save(top)

    q_a = Question(
        topic_id=top.id,
        prompt="Espaços Vetoriais?",
        expected_answer="Linearidade",
    )
    q_repo.save(q_a)
    q_b = Question(
        topic_id=top.id,
        prompt="Variedades Suaves?",
        expected_answer="Diferenciabilidade",
    )
    q_repo.save(q_b)
    content_repo.attach_question(node_a.id, q_a.id)
    content_repo.attach_question(node_b.id, q_b.id)

    # 1. Caso Inicial: Nó A tem Nv. 1, mas Nó B tem Nv. 1 (< 3 exigido). O nó alvo DEVE estar bloqueado.
    prog_repo.save(
        UserQuestionProgress(
            user_id=test_user.id,
            question_id=q_a.id,
            current_level=1,
            next_review_date=date(2026, 12, 1),
        )
    )
    prog_repo.save(
        UserQuestionProgress(
            user_id=test_user.id,
            question_id=q_b.id,
            current_level=1,  # Abaixo do nível 3 exigido!
            next_review_date=date(2026, 12, 1),
        )
    )

    resp_locked = client.get(f"/study-maps/{s_map.id}/nodes/{node_target.id}")
    assert resp_locked.status_code == 200
    html_locked = resp_locked.text

    # Verifica status de bloqueio com formato especificado
    assert "Selado — Requer:" in html_locked
    assert "Álgebra Linear (Nv. 1)" in html_locked
    assert "Cálculo Diferencial (Nv. 3)" in html_locked

    # 2. Caso Desbloqueado: Nó B atinge Nv. 3. O nó alvo DEVE ser destrancado.
    prog_b = prog_repo.get_by_user_and_question(test_user.id, q_b.id)
    assert prog_b is not None
    prog_b.current_level = 3
    prog_repo.save(prog_b)

    resp_unlocked = client.get(f"/study-maps/{s_map.id}/nodes/{node_target.id}")
    assert resp_unlocked.status_code == 200
    html_unlocked = resp_unlocked.text

    assert "Selos Arcanos Satisfeitos (Pronto para Estudo)" in html_unlocked
