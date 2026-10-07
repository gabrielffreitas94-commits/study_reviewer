"""Testes de integração para SqlAlchemyReviewAuditRepository e SqlAlchemyUnitOfWork (Sprint 04)."""

from collections.abc import Generator
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.persistence.repositories import (
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyReviewAuditRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUnitOfWork,
    SqlAlchemyUserRepository,
)
from src.domain.entities import (
    Question,
    ReviewAuditLog,
    Subject,
    Topic,
    User,
    UserQuestionProgress,
)
from src.infrastructure.database import Base


@pytest.fixture
def db_session() -> Generator[Session]:
    """Cria banco SQLite em memória isolado para os testes de integração."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.integration
def test_review_audit_repository_save_and_list_by_user(db_session: Session) -> None:
    """Verifica persistência e listagem paginada de logs de auditoria."""
    user_repo = SqlAlchemyUserRepository(db_session)
    audit_repo = SqlAlchemyReviewAuditRepository(db_session)

    user = User(google_sub="sub-audit-1", email="audit@test.com", name="Audit User")
    user_repo.save(user)
    db_session.commit()

    # Cria 3 logs em datas diferentes
    for i in range(3):
        log = ReviewAuditLog(
            user_id=user.id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name=f"Matéria {i}",
            historical_topic_name=f"Tema {i}",
            review_date=date(2026, 10, i + 1),
            score=100,
            level_before=i,
            level_after=i + 1,
            evaluation_mode="MANUAL",
            logged_at=datetime(2026, 10, i + 1, 10, 0, 0, tzinfo=UTC),
        )
        audit_repo.save(log)
    db_session.commit()

    # Listagem paginada ordenada decrescente por data
    logs_p1 = audit_repo.list_by_user(user_id=user.id, limit=2, offset=0)
    assert len(logs_p1) == 2
    assert logs_p1[0].review_date == date(2026, 10, 3)
    assert logs_p1[1].review_date == date(2026, 10, 2)

    logs_p2 = audit_repo.list_by_user(user_id=user.id, limit=2, offset=2)
    assert len(logs_p2) == 1
    assert logs_p2[0].review_date == date(2026, 10, 1)

    # Contagem total
    assert audit_repo.count_by_user(user.id) == 3


@pytest.mark.integration
@pytest.mark.security
def test_review_audit_repository_filter_by_subject_and_multi_tenancy(
    db_session: Session,
) -> None:
    """Verifica isolamento multi-tenant e filtragem correta por subject_id.

    Vulnerabilidade prevenida: Insecure Direct Object Reference (IDOR - CWE-639).
    Garantia de segurança: O estudante só acessa seus próprios logs e a filtragem por matéria
    não expõe registros de terceiros nem vaza existência de IDs de outros usuários.
    """
    user_repo = SqlAlchemyUserRepository(db_session)
    audit_repo = SqlAlchemyReviewAuditRepository(db_session)

    user_a = User(google_sub="sub-a", email="a@test.com", name="User A")
    user_b = User(google_sub="sub-b", email="b@test.com", name="User B")
    user_repo.save(user_a)
    user_repo.save(user_b)
    db_session.commit()

    subj_1 = uuid4()
    subj_2 = uuid4()

    # Log do User A na Matéria 1
    audit_repo.save(
        ReviewAuditLog(
            user_id=user_a.id,
            question_id=uuid4(),
            subject_id=subj_1,
            topic_id=uuid4(),
            historical_subject_name="Matéria 1",
            historical_topic_name="Tema 1",
            review_date=date(2026, 10, 5),
            score=100,
            level_before=0,
            level_after=1,
        )
    )
    # Log do User A na Matéria 2
    audit_repo.save(
        ReviewAuditLog(
            user_id=user_a.id,
            question_id=uuid4(),
            subject_id=subj_2,
            topic_id=uuid4(),
            historical_subject_name="Matéria 2",
            historical_topic_name="Tema 2",
            review_date=date(2026, 10, 6),
            score=50,
            level_before=1,
            level_after=1,
        )
    )
    # Log do User B na Matéria 1
    audit_repo.save(
        ReviewAuditLog(
            user_id=user_b.id,
            question_id=uuid4(),
            subject_id=subj_1,
            topic_id=uuid4(),
            historical_subject_name="Matéria 1",
            historical_topic_name="Tema B",
            review_date=date(2026, 10, 5),
            score=100,
            level_before=0,
            level_after=1,
        )
    )
    db_session.commit()

    # User A filtrando por subj_1: retorna apenas 1
    filtered_a = audit_repo.list_by_user(user_id=user_a.id, subject_id=subj_1)
    assert len(filtered_a) == 1
    assert filtered_a[0].historical_subject_name == "Matéria 1"
    assert audit_repo.count_by_user(user_id=user_a.id, subject_id=subj_1) == 1

    # User B não vê os registros do User A
    assert audit_repo.count_by_user(user_id=user_b.id) == 1


@pytest.mark.integration
def test_review_audit_repository_stream_and_active_dates(db_session: Session) -> None:
    """Verifica stream_by_user em lote e contagem de datas ativas."""
    user_repo = SqlAlchemyUserRepository(db_session)
    audit_repo = SqlAlchemyReviewAuditRepository(db_session)

    user = User(google_sub="sub-stream", email="stream@test.com", name="Stream User")
    user_repo.save(user)
    db_session.commit()

    # Insere 5 logs em 2 datas distintas
    for i in range(5):
        d = date(2026, 10, 10) if i < 3 else date(2026, 10, 11)
        audit_repo.save(
            ReviewAuditLog(
                user_id=user.id,
                question_id=uuid4(),
                subject_id=uuid4(),
                topic_id=uuid4(),
                historical_subject_name="Biologia",
                historical_topic_name="Genética",
                review_date=d,
                score=100,
                level_before=0,
                level_after=1,
            )
        )
    db_session.commit()

    # Contagem de datas ativas distintas deve ser 2
    assert audit_repo.get_active_dates_count(user.id) == 2

    # Streaming deve retornar todos os 5 logs
    stream_items = list(audit_repo.stream_by_user(user.id, chunk_size=2))
    assert len(stream_items) == 5

    # get_all_by_user deve retornar todos os 5 ordenados ascendentemente
    all_items = audit_repo.get_all_by_user(user.id)
    assert len(all_items) == 5
    assert all_items[0].review_date == date(2026, 10, 10)
    assert all_items[-1].review_date == date(2026, 10, 11)


@pytest.mark.integration
def test_question_progress_repository_list_by_user(db_session: Session) -> None:
    """Verifica list_by_user em SqlAlchemyQuestionProgressRepository."""
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)

    user = User(google_sub="sub-prog", email="prog@test.com", name="Prog User")
    user_repo.save(user)
    subj = Subject(name="Química", owner_id=user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Orgânica")
    top_repo.save(topic)
    q = Question(topic_id=topic.id, prompt="Carbono?", expected_answer="Tetravalente")
    q_repo.save(q)

    prog = UserQuestionProgress(
        user_id=user.id,
        question_id=q.id,
        current_level=4,
        next_review_date=date(2026, 10, 7),
    )
    prog_repo.save(prog)
    db_session.commit()

    user_progs = prog_repo.list_by_user(user.id)
    assert len(user_progs) == 1
    assert user_progs[0].current_level == 4


@pytest.mark.integration
def test_unit_of_work_commit_and_rollback(db_session: Session) -> None:
    """Verifica controle transacional ACID de SqlAlchemyUnitOfWork."""
    user_repo = SqlAlchemyUserRepository(db_session)
    audit_repo = SqlAlchemyReviewAuditRepository(db_session)
    uow = SqlAlchemyUnitOfWork(db_session)

    user = User(google_sub="sub-uow", email="uow@test.com", name="UoW User")
    user_repo.save(user)
    db_session.commit()

    log1 = ReviewAuditLog(
        user_id=user.id,
        question_id=uuid4(),
        subject_id=uuid4(),
        topic_id=uuid4(),
        historical_subject_name="História",
        historical_topic_name="Brasil",
        review_date=date(2026, 10, 7),
        score=100,
        level_before=0,
        level_after=1,
    )
    audit_repo.save(log1)
    uow.commit()

    assert len(audit_repo.list_by_user(user.id)) == 1

    # Tenta salvar outro e faz rollback
    log2 = ReviewAuditLog(
        user_id=user.id,
        question_id=uuid4(),
        subject_id=uuid4(),
        topic_id=uuid4(),
        historical_subject_name="História",
        historical_topic_name="Império",
        review_date=date(2026, 10, 8),
        score=100,
        level_before=1,
        level_after=2,
    )
    audit_repo.save(log2)
    uow.rollback()

    assert len(audit_repo.list_by_user(user.id)) == 1


@pytest.mark.integration
def test_review_audit_log_preservation_on_foreign_key_delete(db_session: Session) -> None:
    """UC-S04-45: Snapshot Isolation e ON DELETE SET NULL garantem histórico indelével."""
    user_repo = SqlAlchemyUserRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    audit_repo = SqlAlchemyReviewAuditRepository(db_session)

    user = User(google_sub="sub-del", email="del@test.com", name="Delete Test")
    user_repo.save(user)
    subj = Subject(name="Direito Constitucional", owner_id=user.id)
    subj_repo.save(subj)
    topic = Topic(subject_id=subj.id, name="Controle de Constitucionalidade")
    top_repo.save(topic)
    q = Question(topic_id=topic.id, prompt="O que é ADI?", expected_answer="Ação Direta")
    q_repo.save(q)
    db_session.commit()

    audit_log = ReviewAuditLog(
        user_id=user.id,
        question_id=q.id,
        subject_id=subj.id,
        topic_id=topic.id,
        historical_subject_name="Direito Constitucional",
        historical_topic_name="Controle de Constitucionalidade",
        review_date=date(2026, 10, 7),
        score=100,
        level_before=2,
        level_after=3,
        evaluation_mode="MANUAL",
        logged_at=datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC),
    )
    audit_repo.save(audit_log)
    db_session.commit()

    # Exclui a pergunta
    q_repo.delete(q.id)
    db_session.commit()

    # O log ainda existe com os nomes congelados
    logs = audit_repo.list_by_user(user.id)
    assert len(logs) == 1
    assert logs[0].historical_subject_name == "Direito Constitucional"
    assert logs[0].historical_topic_name == "Controle de Constitucionalidade"
    assert logs[0].score == 100
