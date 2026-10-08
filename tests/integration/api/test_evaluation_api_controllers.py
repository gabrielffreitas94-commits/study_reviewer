"""Testes de integração para avaliação de respostas e tokens (Sprint 08)."""

from collections.abc import Generator
from datetime import date
from typing import Any
from unittest.mock import patch
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
    SqlAlchemyTokenLedgerRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import (
    Question,
    Subject,
    TokenLedger,
    Topic,
    User,
    UserQuestionProgress,
)
from src.domain.exceptions import EvaluationServiceError
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-api-eval-1",
        email="eval.user@studyreviewer.local",
        name="Evaluation Student",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-api-eval-2",
        email="other.eval@studyreviewer.local",
        name="Other Student",
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
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session, test_user: User) -> Generator[TestClient]:
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
def test_evaluate_text_answer_success_lifecycle(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    ledger_repo = SqlAlchemyTokenLedgerRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Biologia Celular", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Mitocôndrias")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Qual a função da mitocôndria?",
        expected_answer=(
            "A mitocôndria é a organela responsável pela respiração celular e síntese de ATP."
        ),
    )
    q_repo.save(q)

    # Concede saldo de tokens inicial
    ledger = TokenLedger(user_id=test_user.id, balance=1000)
    ledger_repo.save(ledger)
    db_session.commit()

    # 1. Submissão de resposta válida
    payload = {
        "student_answer": (
            "A mitocôndria é a organela responsável pela respiração celular e síntese de ATP."
        )
    }
    resp = client.post(f"/api/v1/questions/{q.id}/evaluate-text", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_id"] == str(q.id)
    assert data["score"] >= 80
    assert "feedback" in data
    assert data["level_before"] == 0
    assert data["level_after"] == 1
    assert data["tokens_deducted"] > 0
    assert data["remaining_token_balance"] < 1000
    assert data["evaluation_mode"] == "AI_TEXT"


@pytest.mark.integration
def test_evaluate_text_answer_empty_payload_validation(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)
    db_session.commit()

    # Espaços em branco -> 400 DomainValidationError
    resp_whitespace = client.post(
        f"/api/v1/questions/{uuid4()}/evaluate-text", json={"student_answer": "   "}
    )
    assert resp_whitespace.status_code == 400
    assert "não pode ser vazia" in resp_whitespace.json()["detail"]

    # String vazia -> 422 Pydantic Validation Error
    resp_empty = client.post(
        f"/api/v1/questions/{uuid4()}/evaluate-text", json={"student_answer": ""}
    )
    assert resp_empty.status_code == 422


@pytest.mark.integration
def test_evaluate_text_answer_question_not_found(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)
    db_session.commit()

    resp = client.post(
        f"/api/v1/questions/{uuid4()}/evaluate-text",
        json={"student_answer": "Resposta qualquer"},
    )
    assert resp.status_code == 404
    assert "Pergunta não encontrada" in resp.json()["detail"]


@pytest.mark.integration
@pytest.mark.security
def test_evaluate_text_answer_unauthorized_forbidden(
    client: TestClient,
    db_session: Session,
    test_user: User,
    other_user: User,
) -> None:
    """Vulnerabilidade prevenida: Quebra de controle de acesso e IDOR em estudo de perguntas.

    Garantia de segurança: Garante que um estudante não possa submeter respostas nem consumir
    recursos de perguntas associadas a matérias privadas de terceiros.
    """
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)

    user_repo.save(test_user)
    user_repo.save(other_user)

    subj = Subject(name="Privada de Outro", owner_id=other_user.id, is_public=False)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Tópico Privado")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Pergunta secreta?",
        expected_answer="Gabarito secreto",
    )
    q_repo.save(q)
    db_session.commit()

    resp = client.post(
        f"/api/v1/questions/{q.id}/evaluate-text",
        json={"student_answer": "Tentando responder pergunta de terceiro"},
    )
    assert resp.status_code == 403
    assert "Acesso negado" in resp.json()["detail"]


@pytest.mark.integration
def test_evaluate_text_answer_insufficient_tokens_402(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    ledger_repo = SqlAlchemyTokenLedgerRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Direito", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Contratos")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Conceitue contrato.",
        expected_answer="Negócio jurídico bilateral.",
    )
    q_repo.save(q)

    # Saldo insuficiente (apenas 50 tokens, exige 500)
    ledger = TokenLedger(user_id=test_user.id, balance=50)
    ledger_repo.save(ledger)
    db_session.commit()

    resp = client.post(
        f"/api/v1/questions/{q.id}/evaluate-text",
        json={"student_answer": "Contrato é um acordo de vontades."},
    )
    assert resp.status_code == 402
    assert "Saldo insuficiente de tokens" in resp.json()["detail"]


@pytest.mark.integration
def test_evaluate_text_answer_question_not_due_400(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)
    ledger_repo = SqlAlchemyTokenLedgerRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Matéria", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Tema")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Pergunta agendada no futuro?",
        expected_answer="Gabarito",
    )
    q_repo.save(q)

    # Progresso agendado para o futuro
    prog = UserQuestionProgress(
        user_id=test_user.id,
        question_id=q.id,
        current_level=2,
        next_review_date=date(2099, 1, 1),
    )
    prog_repo.save(prog)

    ledger = TokenLedger(user_id=test_user.id, balance=1000)
    ledger_repo.save(ledger)
    db_session.commit()

    resp = client.post(
        f"/api/v1/questions/{q.id}/evaluate-text",
        json={"student_answer": "Tentativa prematura de responder."},
    )
    assert resp.status_code == 400
    assert "não está vencida para revisão" in resp.json()["detail"]


@pytest.mark.integration
def test_evaluate_text_answer_ai_service_error_503(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    ledger_repo = SqlAlchemyTokenLedgerRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Matéria", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Tema")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Pergunta com falha?",
        expected_answer="Gabarito",
    )
    q_repo.save(q)

    ledger = TokenLedger(user_id=test_user.id, balance=1000)
    ledger_repo.save(ledger)
    db_session.commit()

    with patch(
        "src.adapters.ai.gemini_adapters.GeminiAnswerEvaluationAdapter.evaluate_answer",
        side_effect=EvaluationServiceError("Serviço temporariamente indisponível"),
    ):
        resp = client.post(
            f"/api/v1/questions/{q.id}/evaluate-text",
            json={"student_answer": "Resposta que irá falhar no provedor."},
        )
        assert resp.status_code == 503
        assert "Serviço temporariamente indisponível" in resp.json()["detail"]


@pytest.mark.integration
def test_token_balance_and_deposit_endpoints(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)
    db_session.commit()

    # 1. Consulta de saldo (provisionamento JIT 1000 tokens)
    resp_bal = client.get("/api/v1/users/me/token-balance")
    assert resp_bal.status_code == 200
    bal_data = resp_bal.json()
    assert bal_data["user_id"] == str(test_user.id)
    assert bal_data["balance"] == 1000
    assert bal_data["available_balance"] == 1000

    # 2. Depósito de novos tokens
    resp_dep = client.post("/api/v1/users/me/tokens/deposit", json={"amount": 2500})
    assert resp_dep.status_code == 200
    dep_data = resp_dep.json()
    assert dep_data["balance"] == 3500
    assert dep_data["available_balance"] == 3500

    # 3. Tentativa de depósito com valor inválido
    resp_inv = client.post("/api/v1/users/me/tokens/deposit", json={"amount": 0})
    assert resp_inv.status_code == 422

    # 4. Listagem do extrato de transações
    resp_tx = client.get("/api/v1/users/me/tokens/transactions?limit=10")
    assert resp_tx.status_code == 200
    tx_list = resp_tx.json()
    assert len(tx_list) >= 1
    assert tx_list[0]["transaction_type"] == "DEPOSIT"
    assert tx_list[0]["amount"] == 2500
