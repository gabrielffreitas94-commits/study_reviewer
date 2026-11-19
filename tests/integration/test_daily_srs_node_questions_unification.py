"""Testes de integração para a unificação da Fila Diária SRS com Perguntas de Nós da Árvore de Conhecimento.

Garante que perguntas criadas diretamente em nós de StudyMap/StudyNode:
1. Sejam retornadas na fila de revisão diária (/questions/study e GetDueQuestionsUseCase).
2. Tenham os nomes coalescidos: subject_name = map.title e topic_name = node.title.
3. Possam ser revisadas via ReviewQuestionUseCase sem erro de 'Tema não encontrado'.
4. Registrem logs de auditoria com evaluation_mode WRITTEN_SELF_REVIEW e MANUAL.
5. Assegura redirecionamento da raiz ('/') para '/questions/study' e fallback de _safe_redirect_url para '/study-maps'.
"""

from collections.abc import Generator
from datetime import UTC, date, datetime
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
    SqlAlchemyReviewAuditRepository,
    SqlAlchemyStudyMapRepository,
    SqlAlchemyStudyNodeRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUserRepository,
)
from src.adapters.web.auth_controllers import _safe_redirect_url
from src.application.dto.question_dto import ReviewQuestionInputDTO
from src.application.use_cases.question_use_cases import (
    GetDueQuestionsUseCase,
    ReviewQuestionUseCase,
)
from src.application.use_cases.study_tree_use_cases import CreateNodeQuestionUseCase
from src.domain.entities import (
    StudyMap,
    StudyNode,
    User,
)
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.web.app import app


class FixedClock:
    def __init__(self, today_date: date, now_dt: datetime) -> None:
        self._today = today_date
        self._now = now_dt

    def today(self) -> date:
        return self._today

    def now(self) -> datetime:
        return self._now


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid4(),
        google_sub="local:srs.unification@test.com",
        email="srs.unification@test.com",
        name="Guerreiro do Saber",
    )


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def authenticated_client(db_session: Session, test_user: User) -> Generator[TestClient, None, None]:
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.integration
def test_node_question_daily_srs_queue_and_review(
    db_session: Session, test_user: User, authenticated_client: TestClient
) -> None:
    """Valida que questões de StudyNode aparecem em /questions/study e progridem no SRS."""
    today = date(2026, 10, 27)
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=UTC)
    clock = FixedClock(today, now)

    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)

    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    audit_repo = SqlAlchemyReviewAuditRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)

    # 1. Cria Mapa e Nó de Estudo
    study_map = StudyMap(
        id=uuid4(),
        owner_id=test_user.id,
        title="Álgebra Linear Ancestral",
        description="Domínio dos espaços vetoriais e transformações lineares",
    )
    map_repo.save(study_map)

    study_node = StudyNode(
        id=uuid4(),
        map_id=study_map.id,
        title="Espaços Vetoriais Rúnicos",
        pos_x=100.0,
        pos_y=150.0,
    )
    node_repo.save(study_node)

    # 2. Cria pergunta no Nó
    create_q_uc = CreateNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
        clock=clock,
    )
    q_data = create_q_uc.execute(
        map_id=study_map.id,
        node_id=study_node.id,
        user_id=test_user.id,
        prompt="Qual é a definição de um subespaço vetorial?",
        expected_answer="Um subconjunto não-vazio fechado sob adição e multiplicação escalar.",
    )
    q_id = q_data["id"]

    # 3. Verifica se a pergunta aparece na Fila Diária via GetDueQuestionsUseCase
    get_due_uc = GetDueQuestionsUseCase(
        progress_repo=prog_repo,
        question_repo=q_repo,
        subject_repo=subj_repo,
        topic_repo=top_repo,
        clock=clock,
    )
    due_items = get_due_uc.execute(user_id=test_user.id)
    assert len(due_items) == 1
    assert due_items[0].question_id == q_id
    assert due_items[0].subject_name == "Álgebra Linear Ancestral"
    assert due_items[0].topic_name == "Espaços Vetoriais Rúnicos"

    # 4. Verifica na interface Web GET /questions/study
    web_res = authenticated_client.get("/questions/study")
    assert web_res.status_code == 200
    assert "Qual é a definição de um subespaço vetorial?" in web_res.text
    assert "Álgebra Linear Ancestral" in web_res.text
    assert "Espaços Vetoriais Rúnicos" in web_res.text

    # 5. Revisa a pergunta do Nó via ReviewQuestionUseCase
    review_uc = ReviewQuestionUseCase(
        progress_repo=prog_repo,
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=clock,
        audit_repo=audit_repo,
    )
    review_res = review_uc.execute(
        ReviewQuestionInputDTO(question_id=q_id, score=100),
        user_id=test_user.id,
    )
    assert review_res.previous_level == 0
    assert review_res.new_level == 1
    assert review_res.is_promoted is True

    # 6. Verifica log de auditoria
    logs = audit_repo.list_by_user(user_id=test_user.id, limit=10)
    assert len(logs) == 1
    assert logs[0].question_id == q_id
    assert logs[0].subject_id is None
    assert logs[0].topic_id is None
    assert logs[0].historical_subject_name == "Árvore de Conhecimento"
    assert logs[0].historical_topic_name == "Nó de Estudo"


@pytest.mark.integration
def test_node_question_written_self_review_and_manual_audit_modes(
    db_session: Session, test_user: User
) -> None:
    """Valida revisão de perguntas de nó nos modos WRITTEN_SELF_REVIEW e MANUAL."""
    today = date(2026, 10, 27)
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=UTC)
    clock = FixedClock(today, now)

    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)

    map_repo = SqlAlchemyStudyMapRepository(db_session)
    node_repo = SqlAlchemyStudyNodeRepository(db_session)
    q_repo = SqlAlchemyQuestionRepository(db_session)
    prog_repo = SqlAlchemyQuestionProgressRepository(db_session)
    content_repo = SqlAlchemyNodeContentRepository(db_session)
    audit_repo = SqlAlchemyReviewAuditRepository(db_session)
    top_repo = SqlAlchemyTopicRepository(db_session)
    subj_repo = SqlAlchemySubjectRepository(db_session)

    study_map = StudyMap(id=uuid4(), owner_id=test_user.id, title="Geometria Mística")
    map_repo.save(study_map)
    study_node = StudyNode(id=uuid4(), map_id=study_map.id, title="Círculos Encantados")
    node_repo.save(study_node)

    create_q_uc = CreateNodeQuestionUseCase(
        map_repo=map_repo,
        node_repo=node_repo,
        question_repo=q_repo,
        progress_repo=prog_repo,
        content_repo=content_repo,
        clock=clock,
    )
    q_data = create_q_uc.execute(
        map_id=study_map.id,
        node_id=study_node.id,
        user_id=test_user.id,
        prompt="Como calcular a área de um círculo?",
        expected_answer="Pi vezes o raio ao quadrado.",
    )
    q_id = q_data["id"]

    review_uc = ReviewQuestionUseCase(
        progress_repo=prog_repo,
        question_repo=q_repo,
        topic_repo=top_repo,
        subject_repo=subj_repo,
        clock=clock,
        audit_repo=audit_repo,
    )

    # 1. Revisão com resposta escrita para autoavaliação (WRITTEN_SELF_REVIEW)
    res_written = review_uc.execute(
        ReviewQuestionInputDTO(
            question_id=q_id,
            score=95,
            student_answer="A área é dada por Pi multiplicado pelo raio elevado ao quadrado.",
            evaluation_mode="WRITTEN_SELF_REVIEW",
        ),
        user_id=test_user.id,
    )
    assert res_written.new_level == 1

    # 2. Simula vencimento da próxima revisão para validar modo MANUAL
    prog = prog_repo.get_by_user_and_question(test_user.id, q_id)
    assert prog is not None
    prog.next_review_date = today
    prog_repo.save(prog)

    res_manual = review_uc.execute(
        ReviewQuestionInputDTO(
            question_id=q_id,
            score=100,
            evaluation_mode="MANUAL",
        ),
        user_id=test_user.id,
    )
    assert res_manual.new_level == 2

    logs = audit_repo.list_by_user(user_id=test_user.id, limit=10)
    modes = [log.evaluation_mode for log in logs]
    assert "WRITTEN_SELF_REVIEW" in modes
    assert "MANUAL" in modes
    written_log = next(log for log in logs if log.evaluation_mode == "WRITTEN_SELF_REVIEW")
    assert written_log.student_answer is not None
    assert "Pi multiplicado pelo raio" in written_log.student_answer
    for log in logs:
        assert log.subject_id is None
        assert log.topic_id is None
        assert log.historical_subject_name == "Árvore de Conhecimento"
        assert log.historical_topic_name == "Nó de Estudo"


@pytest.mark.integration
def test_root_and_auth_redirects(authenticated_client: TestClient) -> None:
    """Valida redirecionamento de '/' e sanitização de URLs em _safe_redirect_url."""
    # 1. GET / redireciona para /questions/study (status 303)
    root_res = authenticated_client.get("/", follow_redirects=False)
    assert root_res.status_code == 303
    assert root_res.headers["location"] == "/questions/study"

    # 2. _safe_redirect_url default é /study-maps
    assert _safe_redirect_url(None) == "/study-maps"
    assert _safe_redirect_url("") == "/study-maps"
    assert _safe_redirect_url("https://evil.com") == "/study-maps"
    assert _safe_redirect_url("//evil.com") == "/study-maps"
    assert _safe_redirect_url("/\\evil.com") == "/study-maps"
    assert _safe_redirect_url("/questions/study") == "/questions/study"
