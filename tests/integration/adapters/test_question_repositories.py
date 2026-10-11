"""Testes de integração para os repositórios SQLAlchemy de Perguntas Abertas
e Progresso SRS (Camada 3).
"""

from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.persistence.repositories import (
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import Question, Subject, Topic, User, UserQuestionProgress
from src.infrastructure.database import Base


@pytest.fixture
def db_session() -> Generator[Session]:
    """Cria banco SQLite em memória isolado para os testes de integração."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.integration
def test_question_repository_crud(db_session: Session) -> None:
    """Verifica operações CRUD completas de SqlAlchemyQuestionRepository."""
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)

    user = User(google_sub="sub-q-1", email="q@test.com", name="Question Author")
    user_repo.save(user)
    subj = Subject(name="Direito", owner_id=user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Contratos")
    top_repo.save(topic)

    # 1. Salvar e recuperar
    q1 = Question(
        topic_id=topic.id,
        prompt="O que é evicção?",
        expected_answer="Perda da posse ou propriedade...",
    )
    q2 = Question(
        topic_id=topic.id, prompt="O que é arras?", expected_answer="Sinal de garantia..."
    )
    q_repo.save(q1)
    q_repo.save(q2)

    found1 = q_repo.get_by_id(q1.id)
    assert found1 is not None
    assert found1.prompt == "O que é evicção?"
    assert found1.expected_answer == "Perda da posse ou propriedade..."
    assert found1.topic_id == topic.id

    assert q_repo.get_by_id(uuid4()) is None

    # 2. Listar por tema
    questions = q_repo.list_by_topic(topic.id)
    assert len(questions) == 2
    assert {q.prompt for q in questions} == {"O que é evicção?", "O que é arras?"}

    # 3. Atualizar
    updated_q1 = Question(
        id=q1.id,
        topic_id=topic.id,
        prompt="O que é evicção civil?",
        expected_answer="Nova resposta",
    )
    q_repo.save(updated_q1)
    saved = q_repo.get_by_id(q1.id)
    assert saved is not None
    assert saved.prompt == "O que é evicção civil?"

    # 4. Deletar
    q_repo.delete(q1.id)
    assert q_repo.get_by_id(q1.id) is None
    # Deletar ID inexistente não lança erro
    q_repo.delete(uuid4())


@pytest.mark.integration
def test_question_progress_repository_lifecycle_and_due_queue(db_session: Session) -> None:
    """Verifica ciclo de vida do progresso SRS, ordenação da fila do dia e cálculo de intervalos."""
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)

    user = User(google_sub="sub-prog-1", email="student@test.com", name="Student One")
    user_repo.save(user)
    subj = Subject(name="Medicina", owner_id=user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Fisiologia")
    top_repo.save(topic)

    q1 = Question(topic_id=topic.id, prompt="Q1", expected_answer="A1")
    q2 = Question(topic_id=topic.id, prompt="Q2", expected_answer="A2")
    q3 = Question(topic_id=topic.id, prompt="Q3", expected_answer="A3")
    q4_future = Question(topic_id=topic.id, prompt="Q4", expected_answer="A4")
    for q in (q1, q2, q3, q4_future):
        q_repo.save(q)

    today = date(2026, 10, 10)

    # q1: nível 1, vencida em 2026-10-09
    p1 = UserQuestionProgress(
        user_id=user.id,
        question_id=q1.id,
        current_level=1,
        next_review_date=today - timedelta(days=1),
        last_reviewed_at=datetime(2026, 10, 2, tzinfo=UTC),
    )
    # q2: nível 0, vencida em 2026-10-10
    p2 = UserQuestionProgress(
        user_id=user.id,
        question_id=q2.id,
        current_level=0,
        next_review_date=today,
    )
    # q3: nível 2, vencida em 2026-10-10
    p3 = UserQuestionProgress(
        user_id=user.id,
        question_id=q3.id,
        current_level=2,
        next_review_date=today,
    )
    # q4: nível 1, vence no futuro (2026-10-15)
    p4 = UserQuestionProgress(
        user_id=user.id,
        question_id=q4_future.id,
        current_level=1,
        next_review_date=today + timedelta(days=5),
    )

    for p in (p1, p2, p3, p4):
        prog_repo.save(p)

    # 1. Recuperar progresso individual
    found_p = prog_repo.get_by_user_and_question(user.id, q1.id)
    assert found_p is not None
    assert found_p.current_level == 1
    assert found_p.next_review_date == today - timedelta(days=1)
    assert prog_repo.get_by_user_and_question(user.id, uuid4()) is None

    # 2. Contar pendentes
    assert prog_repo.count_due_questions(user.id, today) == 3

    # 3. Próxima data de revisão no futuro
    next_date = prog_repo.get_next_review_date(user.id, today)
    assert next_date == today + timedelta(days=5)

    # 4. Fila do dia com ordenação determinística
    # Esperado:
    # 1º: q1 (next_review_date anterior)
    # 2º: q2 (hoje, nível 0)
    # 3º: q3 (hoje, nível 2)
    due_items = prog_repo.get_due_questions(user.id, today, limit=10)
    assert len(due_items) == 3
    assert due_items[0].question_id == q1.id
    assert due_items[0].interval_days == 7  # Nível 1 tem intervalo de 7 dias
    assert due_items[0].subject_name == "Medicina"
    assert due_items[0].topic_name == "Fisiologia"

    assert due_items[1].question_id == q2.id
    assert due_items[1].interval_days == 1  # Nível 0 tem intervalo de 1 dia

    assert due_items[2].question_id == q3.id
    assert due_items[2].interval_days == 15  # Nível 2 tem intervalo de 15 dias

    # 5. Filtro por matéria e por tema
    filtered_subj = prog_repo.get_due_questions(user.id, today, subject_id=subj.id)
    assert len(filtered_subj) == 3
    filtered_topic = prog_repo.get_due_questions(user.id, today, topic_id=topic.id)
    assert len(filtered_topic) == 3

    other_topic_id = uuid4()
    assert len(prog_repo.get_due_questions(user.id, today, topic_id=other_topic_id)) == 0

    # 6. Teste de limite
    assert len(prog_repo.get_due_questions(user.id, today, limit=2)) == 2


@pytest.mark.integration
def test_get_due_questions_zero_n_plus_one_query(db_session: Session) -> None:
    """Garante que a listagem de perguntas do dia execute exatamente UMA query SQL (Zero N+1)."""
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)

    user = User(google_sub="sub-perf-1", email="perf@test.com", name="Perf User")
    user_repo.save(user)
    subj = Subject(name="História", owner_id=user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Brasil Colônia")
    top_repo.save(topic)

    # Criar 10 perguntas com progresso vencido
    today = date(2026, 10, 10)
    for i in range(10):
        q = Question(topic_id=topic.id, prompt=f"Pergunta {i}", expected_answer=f"Resposta {i}")
        q_repo.save(q)
        prog_repo.save(
            UserQuestionProgress(
                user_id=user.id, question_id=q.id, current_level=0, next_review_date=today
            )
        )

    # Monitorar queries executadas
    query_count = 0

    def before_cursor_execute(
        conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: bool
    ) -> None:
        nonlocal query_count
        query_count += 1

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        due_items = prog_repo.get_due_questions(user.id, today, limit=50)
        assert len(due_items) == 10
        # Exatamente UMA query SQL para carregar todos os dados (sem N+1 de tópicos ou matérias)
        assert query_count == 1
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


@pytest.mark.integration
def test_initialize_progress_for_questions_idempotent(db_session: Session) -> None:
    """Verifica inicialização em lote de progresso com idempotência (ON CONFLICT DO NOTHING)."""
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)

    user = User(google_sub="sub-init-1", email="init@test.com", name="Init User")
    user_repo.save(user)
    subj = Subject(name="Química", owner_id=user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Orgânica")
    top_repo.save(topic)

    q1 = Question(topic_id=topic.id, prompt="P1", expected_answer="R1")
    q2 = Question(topic_id=topic.id, prompt="P2", expected_answer="R2")
    q_repo.save(q1)
    q_repo.save(q2)

    today = date(2026, 10, 10)

    # 1. Lista vazia não deve quebrar
    prog_repo.initialize_progress_for_questions(user.id, [], today)

    # 2. Inicialização inicial
    prog_repo.initialize_progress_for_questions(user.id, [q1.id, q2.id], today)
    assert prog_repo.count_due_questions(user.id, today) == 2

    # 3. Segunda inicialização para os mesmos IDs (idempotente - não duplica nem lança erro)
    prog_repo.initialize_progress_for_questions(user.id, [q1.id, q2.id], today)
    assert prog_repo.count_due_questions(user.id, today) == 2

    # 4. Se um item já existe com progresso avançado, o batch com ON CONFLICT DO NOTHING não reseta
    p1 = prog_repo.get_by_user_and_question(user.id, q1.id)
    assert p1 is not None
    p1.current_level = 3
    prog_repo.save(p1)

    prog_repo.initialize_progress_for_questions(user.id, [q1.id], today)
    p1_after = prog_repo.get_by_user_and_question(user.id, q1.id)
    assert p1_after is not None
    assert p1_after.current_level == 3


@pytest.mark.integration
def test_get_next_review_date_when_no_future_reviews(db_session: Session) -> None:
    """Verifica que get_next_review_date retorna None quando não existem revisões futuras."""
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)
    assert prog_repo.get_next_review_date(uuid4(), date.today()) is None


@pytest.mark.security
def test_question_repositories_sql_injection_defense(db_session: Session) -> None:
    """Vulnerabilidade prevenida: Injeção de SQL em campos de prompt e resposta de perguntas.

    Garantia de segurança: Assegura que inputs contendo payloads maliciosos de injeção SQL
    sejam neutralizados pela camada ORM parametrizada sem execução indevida.
    """
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)

    user = User(google_sub="sub-sec-1", email="sec@test.com", name="Sec User")
    user_repo.save(user)
    subj = Subject(name="Segurança", owner_id=user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="SQLi")
    top_repo.save(topic)

    malicious_prompt = "'); DROP TABLE questions; --"
    malicious_answer = "' OR '1'='1"

    q = Question(topic_id=topic.id, prompt=malicious_prompt, expected_answer=malicious_answer)
    q_repo.save(q)

    found = q_repo.get_by_id(q.id)
    assert found is not None
    assert found.prompt == malicious_prompt
    assert found.expected_answer == malicious_answer

    # A tabela questions continua existindo e intacta
    all_q = q_repo.list_by_topic(topic.id)
    assert len(all_q) == 1


@pytest.mark.unit
def test_question_progress_repository_initialize_postgresql_dialect() -> None:
    """Verifica ramo do dialeto postgresql em initialize_progress_for_questions."""
    from unittest.mock import MagicMock

    mock_session = MagicMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_session.get_bind.return_value = mock_bind

    repo = SqlAlchemyQuestionProgressRepository(mock_session)
    repo.initialize_progress_for_questions(uuid4(), [uuid4()], date(2026, 10, 10))

    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()
