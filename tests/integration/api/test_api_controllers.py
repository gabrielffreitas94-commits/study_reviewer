"""Testes de integração para os controladores de API REST (Camada 3 - Adaptadores)."""

from collections.abc import Generator
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
    """Entidade de usuário padrão para testes de integração."""
    return User(
        id=uuid4(),
        google_sub="test-sub-api-123",
        email="api.test@studyreviewer.local",
        name="Usuário API Teste",
    )


@pytest.fixture
def client(test_user: User) -> Generator[TestClient]:
    """Cria cliente de testes com banco SQLite em memória isolado e usuário autenticado."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    # Persiste o usuário no banco de testes
    with TestingSession() as session:
        SqlAlchemyUserRepository(session).save(test_user)

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


@pytest.mark.security
def test_security_headers_present_on_api_responses(client: TestClient) -> None:
    """Vulnerabilidade prevenida: Ataques de MIME-sniffing, Clickjacking e XSS por ausência

    de cabeçalhos de proteção.

    Garantia de segurança: Assegura que todas as respostas HTTP incluam os cabeçalhos
    defensivos X-Content-Type-Options: nosniff, X-Frame-Options: DENY e Content-Security-Policy.
    """
    response = client.get("/api/v1/subjects")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in response.headers


@pytest.mark.integration
def test_api_subject_lifecycle(client: TestClient) -> None:
    """Verifica criação, listagem e conflito de duplicidade de Matéria via API REST."""
    # 1. Lista inicial vazia
    resp = client.get("/api/v1/subjects")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Criação válida
    resp_create = client.post("/api/v1/subjects", json={"name": "Direito Administrativo"})
    assert resp_create.status_code == 201
    created = resp_create.json()
    assert created["name"] == "Direito Administrativo"
    assert "id" in created

    # 3. Conflito por nome duplicado
    resp_dup = client.post("/api/v1/subjects", json={"name": "direito administrativo"})
    assert resp_dup.status_code == 409
    assert "já cadastrada" in resp_dup.json()["detail"]

    # 4. Validação de tamanho mínimo
    resp_invalid = client.post("/api/v1/subjects", json={"name": "A"})
    assert resp_invalid.status_code == 422


@pytest.mark.integration
def test_api_topic_lifecycle(client: TestClient) -> None:
    """Verifica criação, listagem e tratamento de erros de Tema via API REST."""
    # Cria matéria de apoio
    sub_resp = client.post("/api/v1/subjects", json={"name": "Biologia Celular"})
    sub_id = sub_resp.json()["id"]

    # Cria tema
    top_resp = client.post("/api/v1/topics", json={"subject_id": sub_id, "name": "Mitocôndrias"})
    assert top_resp.status_code == 201
    assert top_resp.json()["name"] == "Mitocôndrias"

    # Conflito no mesmo tema
    dup_resp = client.post("/api/v1/topics", json={"subject_id": sub_id, "name": "mitocôndrias"})
    assert dup_resp.status_code == 409

    # Matéria inexistente
    missing_sub = client.post("/api/v1/topics", json={"subject_id": str(uuid4()), "name": "Outro"})
    assert missing_sub.status_code == 404

    # Listagem por matéria
    list_resp = client.get(f"/api/v1/subjects/{sub_id}/topics")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


@pytest.mark.integration
def test_api_flashcard_and_study_flow(client: TestClient) -> None:
    """Verifica criação de flashcard e consulta de próximo card via API REST."""
    # Tenta estudar em pool vazia -> 404
    empty_study = client.get("/api/v1/study/next")
    assert empty_study.status_code == 404
    assert "Nenhum flashcard disponível" in empty_study.json()["detail"]

    # Prepara matéria e tema
    sub = client.post("/api/v1/subjects", json={"name": "História"}).json()
    top = client.post(
        "/api/v1/topics", json={"subject_id": sub["id"], "name": "Brasil Colônia"}
    ).json()

    # Cria flashcard com sucesso
    card_resp = client.post(
        "/api/v1/flashcards",
        json={
            "topic_id": top["id"],
            "front": "Em que ano ocorreu o Tratado de Tordesilhas?",
            "back": "1494",
        },
    )
    assert card_resp.status_code == 201
    card_data = card_resp.json()
    assert card_data["front"] == "Em que ano ocorreu o Tratado de Tordesilhas?"
    assert card_data["position"] == 100

    # Criação em tema inexistente
    card_err = client.post(
        "/api/v1/flashcards",
        json={"topic_id": str(uuid4()), "front": "F", "back": "B"},
    )
    assert card_err.status_code == 404

    # Consulta próximo card
    study_resp = client.get(f"/api/v1/study/next?topic_id={top['id']}")
    assert study_resp.status_code == 200
    study_data = study_resp.json()
    assert study_data["id"] == card_data["id"]
    assert study_data["round_number"] == 1
    assert study_data["current_index"] == 1
    assert study_data["total_cards"] == 1


@pytest.mark.integration
def test_api_domain_validation_errors(client: TestClient) -> None:
    """Verifica retorno 422 quando a validação de domínio rejeita inputs com espaços."""
    # Matéria com espaços em branco que resulta em 1 caractere no domínio
    sub_err = client.post("/api/v1/subjects", json={"name": "   A   "})
    assert sub_err.status_code == 422
    assert "entre 2 e 100 caracteres" in sub_err.json()["detail"]

    # Cria matéria válida
    sub = client.post("/api/v1/subjects", json={"name": "Matemática"}).json()

    # Tema com espaços em branco que resulta em 1 caractere no domínio
    top_err = client.post("/api/v1/topics", json={"subject_id": sub["id"], "name": "   X   "})
    assert top_err.status_code == 422
    assert "entre 2 e 100 caracteres" in top_err.json()["detail"]

    # Cria tema válido
    top = client.post("/api/v1/topics", json={"subject_id": sub["id"], "name": "Álgebra"}).json()

    # Flashcard com frente que resulta em string vazia após strip
    card_err = client.post(
        "/api/v1/flashcards",
        json={"topic_id": top["id"], "front": "     ", "back": "Resposta válida"},
    )
    assert card_err.status_code == 422
    assert "entre 1 e 5.000 caracteres" in card_err.json()["detail"]


@pytest.mark.integration
def test_api_study_next_with_empty_or_invalid_query_params(client: TestClient) -> None:
    """Verifica que /api/v1/study/next tolera query params vazios ou inválidos."""
    resp1 = client.get("/api/v1/study/next?subject_id=&topic_id=")
    assert resp1.status_code == 404  # Pool vazia (tratado como None)

    resp2 = client.get("/api/v1/study/next?subject_id=invalid&topic_id=not-a-uuid")
    assert resp2.status_code == 404


@pytest.mark.integration
def test_api_study_batch_lifecycle(client: TestClient) -> None:
    """Verifica consulta de lote paginado de flashcards via API REST."""
    # Pool vazia -> 404
    empty_batch = client.get("/api/v1/study/batch")
    assert empty_batch.status_code == 404
    assert "Nenhum flashcard disponível" in empty_batch.json()["detail"]

    # Cria matéria, tema e flashcard
    sub = client.post("/api/v1/subjects", json={"name": "Direito Constitucional"}).json()
    top = client.post(
        "/api/v1/topics", json={"subject_id": sub["id"], "name": "Direitos Fundamentais"}
    ).json()
    card_resp = client.post(
        "/api/v1/flashcards",
        json={
            "topic_id": top["id"],
            "front": "O que é o Habeas Corpus?",
            "back": "Remédio constitucional para proteger liberdade de locomoção.",
        },
    )
    assert card_resp.status_code == 201
    card_data = card_resp.json()

    # Consulta lote por topic_id
    batch_resp = client.get(f"/api/v1/study/batch?topic_id={top['id']}&limit=50")
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["total_cards"] == 1
    assert batch_data["round_number"] == 1
    assert batch_data["has_more"] is False
    assert len(batch_data["cards"]) == 1
    assert batch_data["cards"][0]["id"] == card_data["id"]

    # Consulta lote por subject_id
    batch_sub = client.get(f"/api/v1/study/batch?subject_id={sub['id']}")
    assert batch_sub.status_code == 200
    assert batch_sub.json()["total_cards"] == 1


@pytest.mark.integration
def test_api_mark_card_read(client: TestClient) -> None:
    """Verifica endpoint de marcar card lido e avançar sessão de estudo."""
    # Card inexistente -> 404
    missing_resp = client.post(f"/api/v1/study/read/{uuid4()}")
    assert missing_resp.status_code == 404
    assert "Card não encontrado" in missing_resp.json()["detail"]

    # Cria matéria, tema e flashcard
    sub = client.post("/api/v1/subjects", json={"name": "Informática"}).json()
    top = client.post(
        "/api/v1/topics", json={"subject_id": sub["id"], "name": "Redes de Computadores"}
    ).json()
    card = client.post(
        "/api/v1/flashcards",
        json={
            "topic_id": top["id"],
            "front": "O que é TCP?",
            "back": "Transmission Control Protocol",
        },
    ).json()

    # Leitura sem sessão ativa (não quebra, retorna ok)
    read_no_session = client.post(f"/api/v1/study/read/{card['id']}")
    assert read_no_session.status_code == 200
    assert read_no_session.json() == {"status": "ok"}

    # Inicia sessão com subject_id e topic_id
    client.get(f"/api/v1/study/next?topic_id={top['id']}&subject_id={sub['id']}")

    # Marca lido com sessão ativa
    read_resp = client.post(
        f"/api/v1/study/read/{card['id']}?topic_id={top['id']}&subject_id={sub['id']}"
    )
    assert read_resp.status_code == 200
    assert read_resp.json() == {"status": "ok"}


def test_health_check_endpoint(client: TestClient) -> None:
    """Verifica que o endpoint /health responde 200 com status healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "environment" in data
    assert "storage" in data


@pytest.mark.integration
def test_api_study_next_with_current_index_completes_round(client: TestClient) -> None:
    """Verifica que a API /study/next reconhece current_index e conclui a rodada."""
    sub = client.post("/api/v1/subjects", json={"name": "Física"}).json()
    top = client.post("/api/v1/topics", json={"subject_id": sub["id"], "name": "Mecânica"}).json()
    client.post(
        "/api/v1/flashcards",
        json={"topic_id": top["id"], "front": "Velocidade", "back": "v = d/t"},
    )

    # Inicia a sessão
    resp1 = client.get(f"/api/v1/study/next?topic_id={top['id']}")
    assert resp1.status_code == 200
    assert resp1.json()["current_index"] == 1
    assert resp1.json()["round_number"] == 1

    # Próximo card informando que completou o card 1 (total = 1 card)
    resp2 = client.get(f"/api/v1/study/next?topic_id={top['id']}&current_index=1")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["round_shuffled"] is True
    assert data2["round_number"] == 2
    assert data2["current_index"] == 1
