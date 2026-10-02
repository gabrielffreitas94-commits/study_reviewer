"""Testes de integração para os controladores Web e templates (Camada 3 - Adaptadores)."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.database import Base, get_db
from src.infrastructure.web.app import app


@pytest.fixture
def client() -> Generator[TestClient]:
    """Cria cliente de testes com banco SQLite em memória isolado."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    def override_get_db() -> Generator[Session]:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.mark.integration
def test_root_redirects_to_study(client: TestClient) -> None:
    """Verifica se a rota raiz '/' redireciona para '/study'."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/study"


@pytest.mark.integration
def test_study_view_empty_pool(client: TestClient) -> None:
    """Acesso à tela de estudo com pool vazia renderiza estado vazio convidativo."""
    response = client.get("/study")
    assert response.status_code == 200
    assert "Nenhum Flashcard Disponível" in response.text
    assert "Cadastrar Primeiro Flashcard" in response.text


@pytest.mark.integration
def test_full_web_flashcard_flow(client: TestClient) -> None:
    """Fluxo completo web: cria matéria, tema, card, estuda, vira e avança."""
    # 1. Cria Matéria
    resp_sub = client.post(
        "/subjects", data={"name": "Direito Constitucional"}, follow_redirects=False
    )
    assert resp_sub.status_code == 303

    # Obtém ID da matéria criada
    resp_list_subs = client.get("/subjects")
    assert resp_list_subs.status_code == 200
    assert "Direito Constitucional" in resp_list_subs.text

    # 2. Cria Tema via API para obter o UUID com precisão
    resp_api_sub = client.get("/api/v1/subjects")
    sub_id = resp_api_sub.json()[0]["id"]

    resp_top = client.post(
        "/topics",
        data={"subject_id": sub_id, "name": "Direitos Fundamentais"},
        follow_redirects=False,
    )
    assert resp_top.status_code == 303

    resp_api_top = client.get(f"/api/v1/subjects/{sub_id}/topics")
    top_id = resp_api_top.json()[0]["id"]

    # 3. Acessa tela de cadastro de flashcard (com chips e busca fuzzy)
    resp_new = client.get(f"/flashcards/new?topic_id={top_id}")
    assert resp_new.status_code == 200
    assert "Cadastrar Flashcard" in resp_new.text
    assert "selected-chips-container" in resp_new.text
    assert "topic-search-input" in resp_new.text
    assert "btn-clear-all-chips" in resp_new.text

    # 4. Cadastra primeiro card com o botão único Salvar Flashcard
    resp_card1 = client.post(
        "/flashcards",
        data={
            "topic_id": top_id,
            "front": "O que é habeas corpus?",
            "back": "Remédio constitucional que protege a liberdade de locomoção.",
        },
        follow_redirects=False,
    )
    assert resp_card1.status_code == 303
    assert "success=1" in resp_card1.headers["location"]

    # 5. Cadastra segundo card mantendo fluxo ágil contínuo
    resp_card2 = client.post(
        "/flashcards",
        data={
            "topic_id": top_id,
            "front": "O que é mandado de segurança?",
            "back": "Protege direito líquido e certo não amparado por HC ou HD.",
        },
        follow_redirects=False,
    )
    assert resp_card2.status_code == 303
    assert "success=1" in resp_card2.headers["location"]

    # 6. Usuário acessa aba /study para iniciar o estudo
    resp_study = client.get(f"/study?topic_id={top_id}")
    assert resp_study.status_code == 200
    assert "Card" in resp_study.text
    assert "Rodada 1" in resp_study.text

    # 7. Testa Flip do card via HTMX
    # Recupera o card atual via API para obter id e position
    resp_next_api = client.get(f"/api/v1/study/next?topic_id={top_id}")
    current_card = resp_next_api.json()

    resp_flip = client.post(
        "/study/flip",
        data={
            "card_id": current_card["id"],
            "side": "front",
            "current_index": 1,
            "total_cards": 2,
            "round_number": 1,
            "position": current_card["position"],
        },
    )
    assert resp_flip.status_code == 200
    assert "Resposta (Verso)" in resp_flip.text

    # 8. Testa Flip de volta para Frente
    resp_flip_back = client.post(
        "/study/flip",
        data={
            "card_id": current_card["id"],
            "side": "back",
            "current_index": 1,
            "total_cards": 2,
            "round_number": 1,
            "position": current_card["position"],
        },
    )
    assert resp_flip_back.status_code == 200
    assert "Pergunta (Frente)" in resp_flip_back.text

    # 9. Testa Next Card via HTMX
    resp_next = client.post(
        "/study/next",
        data={"topic_id": top_id},
    )
    assert resp_next.status_code == 200
    assert "flashcard-container" in resp_next.text


@pytest.mark.integration
def test_web_validation_errors(client: TestClient) -> None:
    """Verifica retorno de erros amigáveis nos formulários web."""
    # Criação de matéria com nome vazio
    resp_sub_err = client.post("/subjects", data={"name": "   "})
    assert resp_sub_err.status_code == 400
    assert "Nome da matéria deve ter entre 2 e 100 caracteres" in resp_sub_err.text

    # Criação de tema com nome vazio
    sub_id = uuid4()
    resp_top_err = client.post("/topics", data={"subject_id": str(sub_id), "name": " "})
    assert resp_top_err.status_code == 400

    # Criação de flashcard com frente vazia
    resp_card_err = client.post(
        "/flashcards",
        data={"topic_id": str(sub_id), "front": "", "back": "Resposta válida"},
    )
    assert resp_card_err.status_code == 400


@pytest.mark.integration
def test_flip_card_not_found(client: TestClient) -> None:
    """Flip em card inexistente retorna partial com card=None."""
    resp = client.post(
        "/study/flip",
        data={
            "card_id": str(uuid4()),
            "side": "front",
            "current_index": 1,
            "total_cards": 1,
            "round_number": 1,
            "position": 100,
        },
    )
    assert resp.status_code == 200
    assert "Nenhum card disponível" in resp.text


@pytest.mark.integration
def test_next_card_empty_pool(client: TestClient) -> None:
    """Avanço de card via HTMX em pool vazia retorna estado vazio."""
    resp = client.post("/study/next", data={"subject_id": "", "topic_id": ""})
    assert resp.status_code == 200
    assert "Nenhum Flashcard Disponível" in resp.text


@pytest.mark.integration
def test_new_flashcard_view_without_filter(client: TestClient) -> None:
    """Tela de novo flashcard sem filtro de matéria carrega todos os temas."""
    sub = client.post("/api/v1/subjects", json={"name": "História Geral"}).json()
    client.post("/api/v1/topics", json={"subject_id": sub["id"], "name": "Roma Antiga"})

    resp = client.get("/flashcards/new")
    assert resp.status_code == 200
    assert "Roma Antiga" in resp.text


@pytest.mark.integration
def test_study_view_with_empty_or_invalid_query_params(client: TestClient) -> None:
    """Requisições GET com query params vazios ou inválidos não devem quebrar com erro 422."""
    sub = client.post("/api/v1/subjects", json={"name": "Filosofia Moderna"}).json()
    resp1 = client.get(f"/study?subject_id={sub['id']}&topic_id=")
    assert resp1.status_code == 200
    assert "Filosofia Moderna" in resp1.text

    resp2 = client.get("/study?subject_id=&topic_id=")
    assert resp2.status_code == 200

    resp3 = client.get("/study?subject_id=invalid-uuid&topic_id=not-a-uuid")
    assert resp3.status_code == 200

    resp4 = client.get(f"/flashcards/new?subject_id={sub['id']}&topic_id=")
    assert resp4.status_code == 200


@pytest.mark.integration
def test_create_flashcard_web_multi_topic_and_single_button(client: TestClient) -> None:
    """Valida cadastro web de flashcard com múltiplos temas e botão único (ADR-004)."""
    sub = client.post("/api/v1/subjects", json={"name": "Ciência Política"}).json()
    t1 = client.post(
        "/api/v1/topics", json={"subject_id": sub["id"], "name": "Sistemas de Governo"}
    ).json()
    t2 = client.post(
        "/api/v1/topics", json={"subject_id": sub["id"], "name": "Poder Executivo"}
    ).json()

    # 1. Envio de flashcard com 2 temas e sem 'action' (padrão botão único 'Salvar')
    resp_create = client.post(
        "/flashcards",
        data={
            "topic_ids": [t1["id"], t2["id"]],
            "front": "Diferença entre Presidencialismo e Parlamentarismo?",
            "back": "No presidencialismo o chefe de Estado é também chefe de governo.",
        },
        follow_redirects=False,
    )
    assert resp_create.status_code == 303
    loc = resp_create.headers["location"]
    assert "success=1" in loc
    assert f"topic_ids={t1['id']}" in loc
    assert f"topic_ids={t2['id']}" in loc

    # 2. Tela de estudo deve exibir os badges dos temas
    resp_study = client.get(f"/study?topic_id={t1['id']}")
    assert resp_study.status_code == 200
    assert "Sistemas de Governo" in resp_study.text
    assert "Poder Executivo" in resp_study.text

    # 3. Tentativa de cadastro com dados inválidos (sem temas) deve retornar erro 400
    resp_err = client.post(
        "/flashcards",
        data={
            "front": "Pergunta sem tema",
            "back": "Resposta sem tema",
        },
        follow_redirects=False,
    )
    assert resp_err.status_code == 400
    assert "Flashcard deve estar associado a pelo menos 1 tema" in resp_err.text
