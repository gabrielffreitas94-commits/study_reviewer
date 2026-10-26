"""Testes de integração para as rotas REST do Tomo do Nó (Grimoire) e Rota Web Dedicada."""

from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyUserRepository,
)
from src.domain.entities import User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-grimoire-owner",
        email="grimoire.owner@test.com",
        name="Grimoire Owner",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-grimoire-intruder",
        email="grimoire.intruder@test.com",
        name="Grimoire Intruder",
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
def test_node_grimoire_api_endpoints_and_dedicated_page(
    authenticated_client: TestClient,
) -> None:
    """Valida o ciclo completo do Tomo do Nó: teoria, perguntas, materiais, revisão livre e tela dedicada."""
    # 1. Cria árvore e nó
    map_res = authenticated_client.post(
        "/api/v1/study-maps",
        json={"title": "Códice de Física", "description": "Mecânica Clássica"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    node_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={"title": "Leis de Newton", "icon": "sword", "pos_x": 100, "pos_y": 100},
    )
    assert node_res.status_code == 201
    node_id = node_res.json()["id"]

    # 2. Salva teoria no Tomo do Nó
    theory_res = authenticated_client.patch(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/theory",
        json={"theory_content": "A resultante das forças é F = m * a."},
    )
    assert theory_res.status_code == 200
    assert theory_res.json()["theory_content"] == "A resultante das forças é F = m * a."

    # 3. Cria provação SRS diretamente no Nó
    q_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions",
        json={
            "prompt": "Enuncie a Segunda Lei de Newton.",
            "expected_answer": "A força resultante é igual à taxa de variação do momento linear (F = ma).",
        },
    )
    assert q_res.status_code == 201
    q_data = q_res.json()
    q_id = q_data["id"]
    assert q_data["prompt"] == "Enuncie a Segunda Lei de Newton."
    assert q_data["statement"] == "Enuncie a Segunda Lei de Newton."
    assert q_data["current_level"] == 0

    # 4. Responde à provação no Nó e sobe para Rank I
    rev_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{q_id}/review",
        json={"score": 100},
    )
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["new_level"] == 1
    assert rev_data["current_question_level"] == 1
    assert rev_data["is_training_only"] is False
    assert rev_data["node_effective_level"] == 1

    # 5. Modo Treino Livre: Imediata segunda revisão no mesmo dia retorna 200 com is_training_only=True
    rev_res2 = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{q_id}/review",
        json={"score": 50},
    )
    assert rev_res2.status_code == 200
    rev_data2 = rev_res2.json()
    assert rev_data2["is_training_only"] is True
    assert rev_data2["new_level"] == 1

    # 6. Cria material inline no Nó
    mat_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/materials",
        json={
            "title": "Pergaminho de Dinâmica",
            "raw_text": "Texto explicativo sobre inércia e ação e reação.",
            "content_type": "TEXT",
        },
    )
    assert mat_res.status_code == 201
    mat_data = mat_res.json()
    mat_id = mat_data["id"]
    assert mat_data["title"] == "Pergaminho de Dinâmica"
    assert mat_data["raw_text"] == "Texto explicativo sobre inércia e ação e reação."

    # 7. Consulta o Hub de Estudo do Nó (inclui theory_content no node e raw_text nos materials)
    hub_res = authenticated_client.get(f"/api/v1/study-maps/{map_id}/nodes/{node_id}/study-hub")
    assert hub_res.status_code == 200
    hub_data = hub_res.json()
    assert hub_data["node"]["theory_content"] == "A resultante das forças é F = m * a."
    assert len(hub_data["materials"]) == 1
    assert (
        hub_data["materials"][0]["raw_text"] == "Texto explicativo sobre inércia e ação e reação."
    )
    assert len(hub_data["all_questions"]) == 1

    # 8. Acessa a Página Dedicada do Nó (Opção B)
    page_res = authenticated_client.get(f"/study-maps/{map_id}/nodes/{node_id}")
    assert page_res.status_code == 200
    html_text = page_res.text
    assert "Códice de Física" in html_text
    assert "Leis de Newton" in html_text
    assert "A resultante das forças é F = m * a." in html_text
    assert "Pergaminho de Dinâmica" in html_text
    assert "Texto explicativo sobre inércia e ação e reação." in html_text
    assert "Enuncie a Segunda Lei de Newton." in html_text

    # 9. Exclui a pergunta
    del_q_res = authenticated_client.delete(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{q_id}"
    )
    assert del_q_res.status_code in (200, 204)

    # 10. Exclui o material
    del_mat_res = authenticated_client.delete(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/materials/{mat_id}"
    )
    assert del_mat_res.status_code in (200, 204)

    # Verifica hub vazio de materiais e perguntas
    hub_res_after = authenticated_client.get(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/study-hub"
    )
    assert hub_res_after.status_code == 200
    assert len(hub_res_after.json()["materials"]) == 0
    assert len(hub_res_after.json()["all_questions"]) == 0


@pytest.mark.integration
def test_create_question_with_statement_alias(authenticated_client: TestClient) -> None:
    """Verifica que o campo 'statement' funciona como alias para 'prompt' no corpo da requisição."""
    map_res = authenticated_client.post(
        "/api/study-maps",
        json={"title": "Árvore de Teste Alias"},
    )
    assert map_res.status_code == 201
    map_id = map_res.json()["id"]

    node_res = authenticated_client.post(
        f"/api/study-maps/{map_id}/nodes",
        json={"title": "Nó Teste"},
    )
    assert node_res.status_code == 201
    node_id = node_res.json()["id"]

    # Cria pergunta usando 'statement'
    q_res = authenticated_client.post(
        f"/api/study-maps/{map_id}/nodes/{node_id}/questions",
        json={
            "statement": "Qual é a capital da França?",
            "expected_answer": "Paris",
        },
    )
    assert q_res.status_code == 201
    data = q_res.json()
    assert data["prompt"] == "Qual é a capital da França?"
    assert data["statement"] == "Qual é a capital da França?"
    assert data["expected_answer"] == "Paris"


@pytest.mark.integration
def test_review_with_difficulty_parameter(authenticated_client: TestClient) -> None:
    """Verifica submissão de revisão usando o parâmetro 'difficulty'."""
    map_res = authenticated_client.post(
        "/api/v1/study-maps",
        json={"title": "Mapa de Dificuldade"},
    )
    map_id = map_res.json()["id"]

    node_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={"title": "Nó de Dificuldade"},
    )
    node_id = node_res.json()["id"]

    q_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions",
        json={"prompt": "Questão Fácil?", "expected_answer": "Sim"},
    )
    q_id = q_res.json()["id"]

    rev_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{q_id}/review",
        json={"difficulty": "EASY"},
    )
    assert rev_res.status_code == 200
    data = rev_res.json()
    assert data["new_level"] == 1
    assert data["is_training_only"] is False


@pytest.mark.integration
def test_node_grimoire_anti_idor_and_security(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
    other_user: User,
) -> None:
    """Garante que usuários sem autorização recebam 403 Forbidden e nós inexistentes recebam 404."""
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(other_user)

    # Cria mapa com test_user (proprietário legítimo)
    map_res = authenticated_client.post(
        "/api/v1/study-maps",
        json={"title": "Mapa Privado", "is_public": False},
    )
    map_id = map_res.json()["id"]

    node_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes",
        json={"title": "Nó Protegido"},
    )
    node_id = node_res.json()["id"]

    q_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions",
        json={"prompt": "Pergunta Secreta", "expected_answer": "Resposta Secreta"},
    )
    q_id = q_res.json()["id"]

    mat_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/materials",
        json={"title": "Material Secreto", "raw_text": "Top secret"},
    )
    mat_id = mat_res.json()["id"]

    # Alterna autenticação para other_user (sem permissão)
    app.dependency_overrides[get_current_user] = lambda: other_user

    # 1. other_user tenta alterar teoria -> 403
    patch_res = authenticated_client.patch(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/theory",
        json={"theory_content": "Hackeado"},
    )
    assert patch_res.status_code == 403

    # 2. other_user tenta adicionar pergunta -> 403
    post_q_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions",
        json={"prompt": "Pergunta Invasora", "expected_answer": "X"},
    )
    assert post_q_res.status_code == 403

    # 3. other_user tenta adicionar material -> 403
    post_m_res = authenticated_client.post(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/materials",
        json={"title": "Material Invasor", "raw_text": "X"},
    )
    assert post_m_res.status_code == 403

    # 4. other_user tenta excluir pergunta -> 403
    del_q_res = authenticated_client.delete(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/questions/{q_id}"
    )
    assert del_q_res.status_code == 403

    # 5. other_user tenta excluir material -> 403
    del_m_res = authenticated_client.delete(
        f"/api/v1/study-maps/{map_id}/nodes/{node_id}/materials/{mat_id}"
    )
    assert del_m_res.status_code == 403

    # 6. other_user tenta acessar página web do nó privado -> 403
    web_res = authenticated_client.get(f"/study-maps/{map_id}/nodes/{node_id}")
    assert web_res.status_code == 403

    # Retorna autenticação para o proprietário legítimo (test_user)
    app.dependency_overrides[get_current_user] = lambda: test_user

    # 7. Nó inexistente em mapa pertencente ao usuário -> 404
    fake_node_id = uuid4()
    not_found_node = authenticated_client.get(f"/study-maps/{map_id}/nodes/{fake_node_id}")
    assert not_found_node.status_code == 404

    # 8. Mapa inexistente -> 404
    fake_map_id = uuid4()
    not_found_map = authenticated_client.get(f"/study-maps/{fake_map_id}/nodes/{fake_node_id}")
    assert not_found_map.status_code == 404
