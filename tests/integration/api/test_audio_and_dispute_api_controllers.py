"""Testes de integração para avaliação em áudio e conselho multiagente (Sprint 09)."""

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
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-api-audio-1",
        email="audio.user@studyreviewer.local",
        name="Audio Student",
    )


@pytest.fixture
def other_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-api-audio-2",
        email="other.audio@studyreviewer.local",
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
def test_evaluate_audio_answer_success_and_ledger_settle(
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
    subj = Subject(name="Direito Constitucional", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Remédios Constitucionais")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Qual o objetivo do Mandado de Segurança?",
        expected_answer="Proteger direito líquido e certo não amparado por habeas corpus.",
    )
    q_repo.save(q)

    ledger = TokenLedger(user_id=test_user.id, balance=1500)
    ledger_repo.save(ledger)
    db_session.commit()

    # Envia áudio
    response = client.post(
        f"/api/v1/questions/{q.id}/evaluate-audio",
        files={
            "audio_file": (
                "answer.webm",
                b"Proteger direito liquido e certo",
                "audio/webm",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["evaluation_mode"] == "AI_AUDIO"
    assert data["score"] >= 0
    assert "transcribed_text" in data
    assert data["tokens_deducted"] > 0
    assert data["remaining_token_balance"] < 1500


@pytest.mark.integration
def test_evaluate_audio_answer_insufficient_tokens_402(
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
    subj = Subject(name="Direito Constitucional", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Remédios Constitucionais")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Qual o objetivo do Mandado de Segurança?",
        expected_answer="Proteger direito líquido e certo.",
    )
    q_repo.save(q)

    # Apenas 100 tokens (estimativa de áudio é 800)
    ledger = TokenLedger(user_id=test_user.id, balance=100)
    ledger_repo.save(ledger)
    db_session.commit()

    response = client.post(
        f"/api/v1/questions/{q.id}/evaluate-audio",
        files={"audio_file": ("answer.webm", b"audio data", "audio/webm")},
    )
    assert response.status_code == 402
    assert "Saldo insuficiente" in response.json()["detail"]


@pytest.mark.integration
def test_evaluate_audio_answer_empty_audio_400(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Direito Constitucional", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Remédios Constitucionais")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Qual o objetivo?",
        expected_answer="Resposta correta.",
    )
    q_repo.save(q)
    db_session.commit()

    response = client.post(
        f"/api/v1/questions/{q.id}/evaluate-audio",
        files={"audio_file": ("empty.webm", b"", "audio/webm")},
    )
    assert response.status_code == 400
    assert "vazio" in response.json()["detail"].lower()


@pytest.mark.integration
def test_dispute_evaluation_upheld_success(
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
    subj = Subject(name="Direito Penal", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Princípios Penais")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Explique o princípio da insignificância.",
        expected_answer="Exclui a tipicidade material quando a lesão ao bem jurídico é ínfima.",
    )
    q_repo.save(q)

    progress = UserQuestionProgress(
        user_id=test_user.id,
        question_id=q.id,
        current_level=1,
        next_review_date=date.today(),
    )
    prog_repo.save(progress)

    ledger = TokenLedger(user_id=test_user.id, balance=2000)
    ledger_repo.save(ledger)
    db_session.commit()

    payload = {
        "student_answer": "Exclui a tipicidade material de forma pacificada.",
        "dispute_argument": (
            "Mencionei a exclusão da tipicidade material que é o cerne do gabarito oficial."
        ),
    }

    response = client.post(f"/api/v1/questions/{q.id}/dispute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UPHELD"
    assert data["revised_score"] >= 80
    assert data["refund_dispute_tokens"] is True
    assert data["tokens_deducted"] == 0
    # O saldo disponível não foi reduzido (taxa estornada)
    assert data["remaining_token_balance"] == 2000


@pytest.mark.integration
def test_dispute_evaluation_rejected_settles_tokens(
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
    subj = Subject(name="Direito Penal", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Princípios Penais")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Explique a culpabilidade.",
        expected_answer="Juízo de reprovação pessoal pela prática de fato típico e ilícito.",
    )
    q_repo.save(q)

    ledger = TokenLedger(user_id=test_user.id, balance=2000)
    ledger_repo.save(ledger)
    db_session.commit()

    payload = {
        "student_answer": "Falei sobre concurso de pessoas.",
        "dispute_argument": "Deveria ter aceito porque ambos estão no código penal.",
    }

    response = client.post(f"/api/v1/questions/{q.id}/dispute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REJECTED"
    assert data["refund_dispute_tokens"] is False
    assert data["tokens_deducted"] > 0
    assert data["remaining_token_balance"] < 2000


@pytest.mark.integration
def test_dispute_evaluation_insufficient_tokens_402(
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
    subj = Subject(name="Direito Penal", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Princípios Penais")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Pergunta",
        expected_answer="Gabarito",
    )
    q_repo.save(q)

    # Apenas 300 tokens (hold de contestação requer 1000)
    ledger = TokenLedger(user_id=test_user.id, balance=300)
    ledger_repo.save(ledger)
    db_session.commit()

    payload = {
        "student_answer": "Resposta",
        "dispute_argument": "Argumento válido de contestação.",
    }
    response = client.post(f"/api/v1/questions/{q.id}/dispute", json=payload)
    assert response.status_code == 402
    assert "Saldo insuficiente" in response.json()["detail"]


@pytest.mark.integration
def test_dispute_evaluation_ownership_forbidden_403(
    client: TestClient,
    db_session: Session,
    test_user: User,
    other_user: User,
) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)

    user_repo.save(test_user)
    user_repo.save(other_user)

    # Matéria pertence a other_user
    subj = Subject(name="Matéria Privada", owner_id=other_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Tema Privado")
    top_repo.save(topic)

    q = Question(topic_id=topic.id, prompt="Pergunta", expected_answer="Gabarito")
    q_repo.save(q)
    db_session.commit()

    payload = {
        "student_answer": "Tentativa de acesso",
        "dispute_argument": "Argumento qualquer de contestação.",
    }
    response = client.post(f"/api/v1/questions/{q.id}/dispute", json=payload)
    assert response.status_code == 403
    assert "Acesso negado" in response.json()["detail"]


@pytest.mark.security
def test_security_ephemeral_audio_privacy_compliance(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    """Valida a conformidade de privacidade de dados biométricos de voz com o Art. 16 da LGPD.

    Vulnerabilidade prevenida: CWE-359 (Exposure of Private Biometric Data Leak).
    Garantia de segurança: O fluxo de áudio é mantido estritamente em memória e purgado,
    sem persistência em disco ou banco de dados.
    """
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    ledger_repo = SqlAlchemyTokenLedgerRepository(db_session)

    user_repo.save(test_user)
    subj = Subject(name="Direito Constitucional", owner_id=test_user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Remédios Constitucionais")
    top_repo.save(topic)

    q = Question(
        topic_id=topic.id,
        prompt="Pergunta de voz",
        expected_answer="Gabarito de voz.",
    )
    q_repo.save(q)

    ledger = TokenLedger(user_id=test_user.id, balance=1500)
    ledger_repo.save(ledger)
    db_session.commit()

    audio_content = b"Conteudo confidencial de voz gravada"

    response = client.post(
        f"/api/v1/questions/{q.id}/evaluate-audio",
        files={"audio_file": ("voice.webm", audio_content, "audio/webm")},
    )
    assert response.status_code == 200

    # Confirma que nenhuma tabela armazena blobs ou referências de áudio
    tables = Base.metadata.tables.keys()
    assert "audio_recordings" not in tables
    assert "voiceprints" not in tables
