"""Testes de integração para os controladores de API REST de Perguntas Abertas (Camada 3)."""

from collections.abc import Generator
from datetime import date
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.repositories import (
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import Question, Subject, Topic, User, UserQuestionProgress
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.security.rate_limiter import reset_rate_limits
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-api-q-1",
        email="q.api@studyreviewer.local",
        name="API Question User",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-api-q-2",
        email="other.api@studyreviewer.local",
        name="Other User",
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
def client(db_engine: Any, test_user: User, other_user: User) -> Generator[TestClient]:
    TestingSession = sessionmaker(bind=db_engine)

    with TestingSession() as session:
        u_repo = SqlAlchemyUserRepository(session)
        u_repo.save(test_user)
        u_repo.save(other_user)

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
    reset_rate_limits()

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_rate_limits()


@pytest.mark.integration
def test_api_due_questions_empty_queue(client: TestClient) -> None:
    """Verifica retorno 200 com lista vazia quando não há perguntas pendentes."""
    res = client.get("/api/v1/questions/due")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total_due"] == 0
    assert data["next_review_date"] is None


@pytest.mark.integration
def test_api_due_questions_and_review_lifecycle(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Verifica fluxo completo de listagem e revisão com recálculo de intervalos."""
    # 1. Cria matéria, tema e pergunta
    with Session(db_engine) as session:
        subj = Subject(name="Direito Administrativo", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="Atos")
        SqlAlchemyTopicRepository(session).save(topic)

    # 2. Cria pergunta via API
    res_create = client.post(
        f"/api/v1/topics/{topic.id}/questions",
        json={
            "prompt": "Quais os requisitos do ato administrativo?",
            "expected_answer": "Competência, finalidade, forma, motivo e objeto.",
        },
    )
    assert res_create.status_code == 201
    q_data = res_create.json()
    question_id = q_data["id"]

    # 3. Consulta fila de perguntas pendentes (entra imediatamente)
    res_due = client.get("/api/v1/questions/due")
    assert res_due.status_code == 200
    due_data = res_due.json()
    assert due_data["total_due"] == 1
    assert len(due_data["items"]) == 1
    assert due_data["items"][0]["question_id"] == question_id
    assert due_data["items"][0]["current_level"] == 0

    # 4. Submete nota 100 (avança de nível para 1, intervalo de 7 dias)
    res_rev = client.post(
        f"/api/v1/questions/{question_id}/review",
        json={"score": 100},
    )
    assert res_rev.status_code == 200
    rev_data = res_rev.json()
    assert rev_data["previous_level"] == 0
    assert rev_data["new_level"] == 1
    assert rev_data["interval_days"] == 7
    assert rev_data["is_promoted"] is True
    assert rev_data["is_regressed"] is False

    # 5. Após revisão, fila do dia fica vazia (Inbox Zero)
    res_due_after = client.get("/api/v1/questions/due")
    assert res_due_after.status_code == 200
    assert res_due_after.json()["total_due"] == 0

    # 6. Tentar revisar novamente a mesma pergunta hoje falha com 400 (QuestionNotDueError)
    res_not_due = client.post(
        f"/api/v1/questions/{question_id}/review",
        json={"score": 100},
    )
    assert res_not_due.status_code == 400
    assert "não está vencida" in res_not_due.json()["detail"]


@pytest.mark.integration
def test_api_question_crud_and_validation(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Verifica operações CRUD e validação de schema na API."""
    with Session(db_engine) as session:
        subj = Subject(name="Biologia", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="Genética")
        SqlAlchemyTopicRepository(session).save(topic)

    # 1. Criação com validação
    res_create = client.post(
        f"/api/v1/topics/{topic.id}/questions",
        json={"prompt": "O que é DNA?", "expected_answer": "Ácido desoxirribonucleico."},
    )
    assert res_create.status_code == 201
    q_id = res_create.json()["id"]

    # 2. Get por ID
    res_get = client.get(f"/api/v1/questions/{q_id}")
    assert res_get.status_code == 200
    assert res_get.json()["prompt"] == "O que é DNA?"

    # 3. List por tema
    res_list = client.get(f"/api/v1/topics/{topic.id}/questions")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # 4. Update
    res_up = client.put(
        f"/api/v1/questions/{q_id}",
        json={
            "prompt": "O que é a molécula de DNA?",
            "expected_answer": "Polímero de nucleotídeos.",
        },
    )
    assert res_up.status_code == 200
    assert res_up.json()["prompt"] == "O que é a molécula de DNA?"

    # 5. Delete
    res_del = client.delete(f"/api/v1/questions/{q_id}")
    assert res_del.status_code == 200
    assert client.get(f"/api/v1/questions/{q_id}").status_code == 404

    # 6. Validação de payload inválido
    res_bad = client.post(
        f"/api/v1/topics/{topic.id}/questions",
        json={"prompt": "a", "expected_answer": ""},
    )
    assert res_bad.status_code in (400, 422)


@pytest.mark.security
def test_api_questions_anti_idor_defenses(
    client: TestClient, other_user: User, db_engine: Any
) -> None:
    """Vulnerabilidade prevenida: Manipulação direta de referências inseguras (IDOR) em perguntas.

    Garantia de segurança: Assegura que um usuário não possa criar, visualizar, editar,
    excluir ou estudar perguntas em matérias privadas pertencentes a outros estudantes.
    """
    with Session(db_engine) as session:
        subj_priv = Subject(name="Privada", owner_id=other_user.id, is_public=False)
        SqlAlchemySubjectRepository(session).save(subj_priv)
        topic_priv = Topic(subject_id=subj_priv.id, name="Tema Priv")
        SqlAlchemyTopicRepository(session).save(topic_priv)
        q = Question(topic_id=topic_priv.id, prompt="Segredo", expected_answer="Confidencial")
        SqlAlchemyQuestionRepository(session).save(q)

    # 1. Criação em tema privado de outro -> 403
    res_create = client.post(
        f"/api/v1/topics/{topic_priv.id}/questions",
        json={"prompt": "Invadir?", "expected_answer": "Não"},
    )
    assert res_create.status_code == 403

    # 2. Leitura de pergunta em matéria privada de outro -> 403
    assert client.get(f"/api/v1/questions/{q.id}").status_code == 403

    # 3. Listagem de perguntas do tema privado de outro -> 403
    assert client.get(f"/api/v1/topics/{topic_priv.id}/questions").status_code == 403

    # 4. Edição de pergunta de outro -> 403
    res_edit = client.put(
        f"/api/v1/questions/{q.id}", json={"prompt": "Hacked", "expected_answer": "Hacked"}
    )
    assert res_edit.status_code == 403

    # 5. Exclusão de pergunta de outro -> 403
    assert client.delete(f"/api/v1/questions/{q.id}").status_code == 403

    # 6. Revisão em matéria privada de outro -> 403
    assert client.post(f"/api/v1/questions/{q.id}/review", json={"score": 100}).status_code == 403


@pytest.mark.security
def test_api_questions_markdown_xss_sanitization(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Vulnerabilidade prevenida: Injeção de Stored XSS através do payload de criação de perguntas.

    Garantia de segurança: Sanitiza tags perigosas (<script>, onerror, onload) no write-time.
    """
    with Session(db_engine) as session:
        subj = Subject(name="WebSec", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="XSS")
        SqlAlchemyTopicRepository(session).save(topic)

    malicious_prompt = (
        "Qual a vulnerabilidade? <script>alert('xss')</script>"
        "<img src='https://safe.com/img.png' onerror='bad()'>"
    )
    malicious_answer = "Resposta com <a href='javascript:void(0)'>Link</a>"

    res = client.post(
        f"/api/v1/topics/{topic.id}/questions",
        json={"prompt": malicious_prompt, "expected_answer": malicious_answer},
    )
    assert res.status_code == 201
    data = res.json()
    assert "<script>" not in data["prompt"]
    assert "onerror" not in data["prompt"]
    assert 'src="https://safe.com/img.png"' in data["prompt"]
    assert "javascript:" not in data["expected_answer"]


@pytest.mark.security
def test_api_questions_rate_limiting_defense(
    client: TestClient, test_user: User, db_engine: Any
) -> None:
    """Vulnerabilidade prevenida: Abuso de submissões de revisão e DoS no SRS.

    Garantia de segurança: Bloqueia rajadas com status 429 quando limite de 60 req/min é excedido.
    """
    with Session(db_engine) as session:
        subj = Subject(name="RateLimit", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="DDoS")
        SqlAlchemyTopicRepository(session).save(topic)
        q = Question(topic_id=topic.id, prompt="Pergunta?", expected_answer="Resposta")
        SqlAlchemyQuestionRepository(session).save(q)
        SqlAlchemyQuestionProgressRepository(session).save(
            UserQuestionProgress(
                user_id=test_user.id, question_id=q.id, next_review_date=date.today()
            )
        )

    # Executa 60 requisições
    for _ in range(60):
        client.post(f"/api/v1/questions/{q.id}/review", json={"score": 100})

    # A 61ª requisição deve ser bloqueada por rate limit
    res_blocked = client.post(f"/api/v1/questions/{q.id}/review", json={"score": 100})
    assert res_blocked.status_code == 429
    assert "Limite de taxa" in res_blocked.json()["detail"]


@pytest.mark.integration
def test_api_questions_edge_cases_and_error_branches(
    client: TestClient, test_user: User, other_user: User, db_engine: Any
) -> None:
    """Verifica todos os branches de erro e validações nos endpoints de API."""
    # 1. _parse_uuid com string inválida
    res_bad_uuid = client.get("/api/v1/questions/due?subject_id=not-a-valid-uuid")
    assert res_bad_uuid.status_code == 200

    # 2. get_due_questions com subject_id inexistente -> 404
    res_no_subj = client.get(f"/api/v1/questions/due?subject_id={uuid4()}")
    assert res_no_subj.status_code == 404

    # 3. get_due_questions com subject_id privado alheio -> 403
    with Session(db_engine) as session:
        subj_priv = Subject(name="Priv1", owner_id=other_user.id, is_public=False)
        SqlAlchemySubjectRepository(session).save(subj_priv)
        topic_priv = Topic(subject_id=subj_priv.id, name="PrivTop")
        SqlAlchemyTopicRepository(session).save(topic_priv)

    res_priv_due = client.get(f"/api/v1/questions/due?subject_id={subj_priv.id}")
    assert res_priv_due.status_code == 403

    # 4. create_question com topic_id inexistente -> 404
    res_no_top_create = client.post(
        f"/api/v1/topics/{uuid4()}/questions",
        json={"prompt": "Valido?", "expected_answer": "Sim"},
    )
    assert res_no_top_create.status_code == 404

    # 5. create_question com prompt em branco pós sanitização -> 400
    with Session(db_engine) as session:
        subj = Subject(name="ValidSubj", owner_id=test_user.id)
        SqlAlchemySubjectRepository(session).save(subj)
        topic = Topic(subject_id=subj.id, name="ValidTop")
        SqlAlchemyTopicRepository(session).save(topic)

    res_bad_prompt = client.post(
        f"/api/v1/topics/{topic.id}/questions",
        json={"prompt": "<script>alert(1)</script>", "expected_answer": "Resposta"},
    )
    assert res_bad_prompt.status_code == 400

    # 6. list_questions com topic_id inexistente -> 404
    assert client.get(f"/api/v1/topics/{uuid4()}/questions").status_code == 404

    # 7. update_question com question_id inexistente -> 404
    assert (
        client.put(
            f"/api/v1/questions/{uuid4()}", json={"prompt": "Nova", "expected_answer": "Resp"}
        ).status_code
        == 404
    )

    # 8. update_question com prompt em branco pós sanitização -> 400
    with Session(db_engine) as session:
        q = Question(topic_id=topic.id, prompt="Pergunta Original", expected_answer="Resp Original")
        SqlAlchemyQuestionRepository(session).save(q)

    res_bad_up = client.put(
        f"/api/v1/questions/{q.id}",
        json={"prompt": "<script>alert(1)</script>", "expected_answer": "Resp"},
    )
    assert res_bad_up.status_code == 400

    # 9. delete_question com question_id inexistente -> 404
    assert client.delete(f"/api/v1/questions/{uuid4()}").status_code == 404

    # 10. review_question com question_id inexistente -> 404
    assert (
        client.post(f"/api/v1/questions/{uuid4()}/review", json={"score": 100}).status_code == 404
    )

    # 11. review_question com nota fora da faixa [0, 100] -> 400
    with Session(db_engine) as session:
        SqlAlchemyQuestionProgressRepository(session).save(
            UserQuestionProgress(
                user_id=test_user.id, question_id=q.id, next_review_date=date.today()
            )
        )

    res_bad_score = client.post(f"/api/v1/questions/{q.id}/review", json={"score": 150})
    assert res_bad_score.status_code == 400
    assert "A nota deve estar entre 0 e 100" in res_bad_score.json()["detail"]
