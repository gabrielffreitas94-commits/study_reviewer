"""Testes de integração para API REST de Flashcards e CORS (Camada 3 - Adaptadores)."""

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyFlashcardRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import Flashcard, Subject, Topic, User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    """Usuário proprietário padrão para os testes de integração."""
    return User(
        id=uuid4(),
        google_sub="test-sub-flashcards-owner",
        email="owner@studyreviewer.local",
        name="Proprietário Teste",
    )


@pytest.fixture
def other_user() -> User:
    """Outro usuário para testes de controle de acesso e IDOR."""
    return User(
        id=uuid4(),
        google_sub="test-sub-flashcards-other",
        email="other@studyreviewer.local",
        name="Outro Usuário",
    )


@pytest.fixture
def client(test_user: User, other_user: User) -> Generator[TestClient]:
    """Cria cliente de testes com banco SQLite em memória isolado e usuário autenticado."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    with TestingSession() as session:
        user_repo = SqlAlchemyUserRepository(session)
        user_repo.save(test_user)
        user_repo.save(other_user)

    def override_get_db() -> Generator[Session]:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.mark.integration
@pytest.mark.security
def test_cors_preflight_and_headers(client: TestClient) -> None:
    """Verifica se as requisições de origens externas recebem cabeçalhos CORS corretos.

    Vulnerabilidade prevenida: Bloqueio de origens válidas e ataques cross-origin sem controle
    CORS.
    Garantia de segurança: Assegura que o servidor responda com cabeçalhos de CORS adequados
    (Access-Control-Allow-Origin, Access-Control-Allow-Credentials, etc.) para clientes móveis
    e navegadores web.
    """
    # 1. Preflight OPTIONS request
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "Content-Type, Authorization",
    }
    response = client.options("/api/v1/flashcards/" + str(uuid4()), headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "PUT" in response.headers.get("access-control-allow-methods", "")

    # 2. GET simples com Origin móvel (Expo / React Native)
    mobile_origin = "http://localhost:8081"
    resp_get = client.get("/health", headers={"Origin": mobile_origin})
    assert resp_get.status_code == 200
    assert resp_get.headers.get("access-control-allow-origin") == mobile_origin


@pytest.mark.integration
def test_list_topic_flashcards_api_success_and_pagination(
    client: TestClient, test_user: User
) -> None:
    """Listagem de flashcards com paginação limit e offset via API REST."""
    # 1. Cria matéria e tema
    resp_sub = client.post("/api/v1/subjects", json={"name": "Direito Civil"})
    assert resp_sub.status_code == 201
    subject_id = resp_sub.json()["id"]

    resp_top = client.post("/api/v1/topics", json={"subject_id": subject_id, "name": "Família"})
    assert resp_top.status_code == 201
    topic_id = resp_top.json()["id"]

    # 2. Cria 3 flashcards
    c1 = client.post(
        "/api/v1/flashcards",
        json={"front": "F1", "back": "V1", "topic_id": topic_id},
    ).json()
    c2 = client.post(
        "/api/v1/flashcards",
        json={"front": "F2", "back": "V2", "topic_id": topic_id},
    ).json()
    c3 = client.post(
        "/api/v1/flashcards",
        json={"front": "F3", "back": "V3", "topic_id": topic_id},
    ).json()

    # 3. Lista página 1 (limit=2, offset=0)
    resp_p1 = client.get(f"/api/v1/topics/{topic_id}/flashcards?limit=2&offset=0")
    assert resp_p1.status_code == 200
    page1 = resp_p1.json()
    assert len(page1) == 2

    # 4. Lista página 2 (limit=2, offset=2)
    resp_p2 = client.get(f"/api/v1/topics/{topic_id}/flashcards?limit=2&offset=2")
    assert resp_p2.status_code == 200
    page2 = resp_p2.json()
    assert len(page2) == 1

    # 5. Valida que a paginação cobriu todos os 3 cards criados sem duplicidade
    all_returned_ids = {c["id"] for c in page1 + page2}
    expected_ids = {c1["id"], c2["id"], c3["id"]}
    assert all_returned_ids == expected_ids
    assert len({c["id"] for c in page1} & {c["id"] for c in page2}) == 0


@pytest.mark.integration
@pytest.mark.security
def test_list_topic_flashcards_api_private_subject_idor_forbidden(
    client: TestClient, other_user: User
) -> None:
    """Bloqueia listagem de cards de tema em matéria privada pertencente a outro usuário.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e vazamento de dados
    de matéria privada.
    Garantia de segurança: Retorna 403 Forbidden ao tentar listar flashcards de um tema pertencente
    a uma matéria privada de outro usuário.
    """
    # Cria matéria privada de outro usuário diretamente no banco
    db_gen = app.dependency_overrides[get_db]()
    session = next(db_gen)
    sub_repo = SqlAlchemySubjectRepository(session)
    top_repo = SqlAlchemyTopicRepository(session)
    card_repo = SqlAlchemyFlashcardRepository(session)

    private_sub = Subject(name="Segredos Outro", owner_id=other_user.id, is_public=False)
    sub_repo.save(private_sub)

    private_top = Topic(subject_id=private_sub.id, name="Tema Privado")
    top_repo.save(private_top)

    card = Flashcard(topic_id=private_top.id, front="Segredo", back="Resposta", position=100)
    card_repo.save(card)

    session.close()

    # Usuário atual (test_user) tenta listar cards da matéria privada do outro usuário
    response = client.get(f"/api/v1/topics/{private_top.id}/flashcards")
    assert response.status_code == 403
    assert "permissão" in response.json()["detail"].lower()


@pytest.mark.integration
def test_list_topic_flashcards_api_topic_not_found(client: TestClient) -> None:
    """Retorna 404 ao tentar listar cards de tema inexistente."""
    response = client.get(f"/api/v1/topics/{uuid4()}/flashcards")
    assert response.status_code == 404
    assert "Tema não encontrado" in response.json()["detail"]


@pytest.mark.integration
def test_update_flashcard_api_success(client: TestClient) -> None:
    """Atualização bem-sucedida de frente e verso do flashcard via PUT."""
    resp_sub = client.post("/api/v1/subjects", json={"name": "Direito Tributário"})
    subject_id = resp_sub.json()["id"]

    resp_top = client.post("/api/v1/topics", json={"subject_id": subject_id, "name": "Impostos"})
    topic_id = resp_top.json()["id"]

    resp_card = client.post(
        "/api/v1/flashcards",
        json={"front": "Frente Inicial", "back": "Verso Inicial", "topic_id": topic_id},
    )
    card_id = resp_card.json()["id"]

    # Atualiza o card
    resp_put = client.put(
        f"/api/v1/flashcards/{card_id}",
        json={"front": "Frente Atualizada", "back": "Verso Atualizado"},
    )
    assert resp_put.status_code == 200
    updated = resp_put.json()
    assert updated["id"] == card_id
    assert updated["front"] == "Frente Atualizada"
    assert updated["back"] == "Verso Atualizado"


@pytest.mark.integration
@pytest.mark.security
def test_update_flashcard_api_anti_xss_sanitization(client: TestClient) -> None:
    """Sanitiza tags executáveis e handlers maliciosos no front e back via PUT.

    Vulnerabilidade prevenida: Stored Cross-Site Scripting (XSS) via campos de frente e
    verso do flashcard.
    Garantia de segurança: Assegura que tags de script e handlers maliciosos sejam expurgados
    via sanitize_html_content antes da persistência.
    """
    resp_sub = client.post("/api/v1/subjects", json={"name": "Segurança Web"})
    subject_id = resp_sub.json()["id"]

    resp_top = client.post("/api/v1/topics", json={"subject_id": subject_id, "name": "XSS"})
    topic_id = resp_top.json()["id"]

    resp_card = client.post(
        "/api/v1/flashcards",
        json={"front": "Frente Inicial", "back": "Verso Inicial", "topic_id": topic_id},
    )
    card_id = resp_card.json()["id"]

    # Envia payload com código malicioso XSS
    malicious_payload = {
        "front": "<b>Pergunta Segura</b><script>alert('xss-front')</script>",
        "back": "Resposta Segura<img src=x onerror=alert('xss-back')>",
    }
    resp_put = client.put(f"/api/v1/flashcards/{card_id}", json=malicious_payload)
    assert resp_put.status_code == 200
    data = resp_put.json()

    assert "<script>" not in data["front"]
    assert "alert(" not in data["front"]
    assert "<b>Pergunta Segura</b>" in data["front"]

    assert "onerror=" not in data["back"]
    assert "alert(" not in data["back"]
    assert "Resposta Segura" in data["back"]


@pytest.mark.integration
@pytest.mark.security
def test_update_flashcard_api_idor_forbidden(client: TestClient, other_user: User) -> None:
    """Impede que um usuário atualize o flashcard pertencente à matéria de outro usuário.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e modificação
    não autorizada de flashcards.
    Garantia de segurança: Retorna 403 Forbidden ao tentar atualizar um flashcard vinculado
    a matéria de outro usuário.
    """
    # Cria matéria, tema e card pertencentes a other_user
    db_gen = app.dependency_overrides[get_db]()
    session = next(db_gen)
    sub_repo = SqlAlchemySubjectRepository(session)
    top_repo = SqlAlchemyTopicRepository(session)
    card_repo = SqlAlchemyFlashcardRepository(session)

    other_sub = Subject(name="Matéria Alheia", owner_id=other_user.id, is_public=True)
    sub_repo.save(other_sub)

    other_top = Topic(subject_id=other_sub.id, name="Tema Alheio")
    top_repo.save(other_top)

    other_card = Flashcard(topic_id=other_top.id, front="Card Alheio", back="Verso", position=100)
    card_repo.save(other_card)

    session.close()

    # test_user tenta editar o card alheio
    resp = client.put(
        f"/api/v1/flashcards/{other_card.id}",
        json={"front": "Hackeado", "back": "Alterado"},
    )
    assert resp.status_code == 403
    assert "permissão" in resp.json()["detail"].lower()


@pytest.mark.integration
def test_update_flashcard_api_not_found(client: TestClient) -> None:
    """Retorna 404 ao tentar atualizar flashcard inexistente."""
    resp = client.put(
        f"/api/v1/flashcards/{uuid4()}",
        json={"front": "Nova Frente", "back": "Novo Verso"},
    )
    assert resp.status_code == 404
    assert "Flashcard não encontrado" in resp.json()["detail"]


@pytest.mark.integration
def test_delete_flashcard_api_success(client: TestClient) -> None:
    """Exclusão de flashcard via DELETE /flashcards/{id} com sucesso."""
    resp_sub = client.post("/api/v1/subjects", json={"name": "Direito Penal"})
    subject_id = resp_sub.json()["id"]

    resp_top = client.post("/api/v1/topics", json={"subject_id": subject_id, "name": "Crimes"})
    topic_id = resp_top.json()["id"]

    resp_card = client.post(
        "/api/v1/flashcards",
        json={"front": "Frente Para Deletar", "back": "Verso", "topic_id": topic_id},
    )
    card_id = resp_card.json()["id"]

    # Deleta o flashcard
    resp_del = client.delete(f"/api/v1/flashcards/{card_id}")
    assert resp_del.status_code == 200
    assert resp_del.json() == {"message": "Flashcard excluído com sucesso."}

    # Verifica que não está mais listado
    resp_list = client.get(f"/api/v1/topics/{topic_id}/flashcards")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 0


@pytest.mark.integration
@pytest.mark.security
def test_delete_flashcard_api_idor_forbidden(client: TestClient, other_user: User) -> None:
    """Impede que um usuário exclua flashcard vinculado a matéria de outro usuário.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR) e exclusão
    não autorizada de flashcards.
    Garantia de segurança: Retorna 403 Forbidden ao tentar excluir flashcard pertencente
    a matéria de outro usuário.
    """
    db_gen = app.dependency_overrides[get_db]()
    session = next(db_gen)
    sub_repo = SqlAlchemySubjectRepository(session)
    top_repo = SqlAlchemyTopicRepository(session)
    card_repo = SqlAlchemyFlashcardRepository(session)

    other_sub = Subject(name="Matéria Alheia 2", owner_id=other_user.id, is_public=True)
    sub_repo.save(other_sub)

    other_top = Topic(subject_id=other_sub.id, name="Tema Alheio 2")
    top_repo.save(other_top)

    other_card = Flashcard(
        topic_id=other_top.id, front="Card Para Não Deletar", back="Verso", position=100
    )
    card_repo.save(other_card)

    session.close()

    # test_user tenta excluir o card de outro usuário
    resp = client.delete(f"/api/v1/flashcards/{other_card.id}")
    assert resp.status_code == 403
    assert "permissão" in resp.json()["detail"].lower()


@pytest.mark.integration
def test_delete_flashcard_api_not_found(client: TestClient) -> None:
    """Retorna 404 ao tentar excluir flashcard inexistente."""
    resp = client.delete(f"/api/v1/flashcards/{uuid4()}")
    assert resp.status_code == 404
    assert "Flashcard não encontrado" in resp.json()["detail"]


@pytest.mark.integration
@pytest.mark.security
def test_update_flashcard_api_domain_validation_error(client: TestClient) -> None:
    """Valida HTTP 422 caso a sanitização resulte em conteúdo violando invariante.

    Vulnerabilidade prevenida: Injeção de payloads maliciosos que, ao serem neutralizados,
    violam a integridade dos dados.
    Garantia de segurança: Retorna 422 Unprocessable Content se o conteúdo sanitizado for
    vazio ou inválido.
    """
    resp_sub = client.post("/api/v1/subjects", json={"name": "Direito Ambiental"})
    subject_id = resp_sub.json()["id"]

    resp_top = client.post("/api/v1/topics", json={"subject_id": subject_id, "name": "Preservação"})
    topic_id = resp_top.json()["id"]

    resp_card = client.post(
        "/api/v1/flashcards",
        json={"front": "Frente Original", "back": "Verso Original", "topic_id": topic_id},
    )
    card_id = resp_card.json()["id"]

    # Envia payload com apenas tags script (sanitizado vira string vazia)
    resp_put = client.put(
        f"/api/v1/flashcards/{card_id}",
        json={"front": "<script></script>", "back": "Verso Válido"},
    )
    assert resp_put.status_code == 422
    assert (
        "frente do flashcard deve ter entre 1 e 5.000 caracteres"
        in resp_put.json()["detail"].lower()
    )
