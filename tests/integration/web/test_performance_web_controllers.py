"""Testes de integração para os controladores Web e templates do Hub de Desempenho (Sprint 04)."""

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
    SqlAlchemyReviewAuditRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import (
    ReviewAuditLog,
    Subject,
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
        google_sub="sub-perf-web-1",
        email="perf.web@test.com",
        name="Performance Web User",
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
def client(db_engine: Any, test_user: User) -> Generator[TestClient]:
    testing_session_local = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    with testing_session_local() as session:
        u_repo = SqlAlchemyUserRepository(session)
        u_repo.save(test_user)
        session.commit()

    def override_get_db() -> Generator[Session]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.mark.integration
def test_performance_hub_empty_state(client: TestClient) -> None:
    """Verifica renderização do estado vazio para estudante sem histórico."""
    response = client.get("/performance")
    assert response.status_code == 200
    html = response.text
    assert "Hub de Desempenho" in html
    assert "Seu Hub de Desempenho está pronto!" in html
    assert "Começar Minhas Revisões" in html
    # Verifica a presença da aba Desempenho no menu
    assert 'href="/performance"' in html
    assert "grid-cols-4" in html


@pytest.mark.integration
def test_performance_hub_with_data(client: TestClient, db_engine: Any, test_user: User) -> None:
    """Verifica renderização dos cards, pirâmide e histórico de auditoria."""
    session_maker = sessionmaker(bind=db_engine)
    with session_maker() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        audit_repo = SqlAlchemyReviewAuditRepository(session)
        prog_repo = SqlAlchemyQuestionProgressRepository(session)

        subj = Subject(name="Direito Administrativo", owner_id=test_user.id)
        subj_repo.save(subj)

        q1 = uuid4()
        audit_repo.save(
            ReviewAuditLog(
                user_id=test_user.id,
                question_id=q1,
                subject_id=subj.id,
                topic_id=uuid4(),
                historical_subject_name="Direito Administrativo",
                historical_topic_name="Atos Administrativos",
                review_date=date(2026, 10, 7),
                score=100,
                level_before=3,
                level_after=4,
            )
        )
        prog_repo.save(
            UserQuestionProgress(
                user_id=test_user.id,
                question_id=q1,
                current_level=4,
            )
        )
        session.commit()

    response = client.get("/performance")
    assert response.status_code == 200
    html = response.text
    assert "100.0%" in html
    assert "Retenção Madura" in html
    assert "Pirâmide de Retenção Espaçada" in html
    assert "Direito Administrativo" in html
    assert "Atos Administrativos" in html
    assert "N3" in html
    assert "N4" in html


@pytest.mark.integration
def test_audit_logs_htmx_partial_pagination_and_filter(
    client: TestClient, db_engine: Any, test_user: User
) -> None:
    """Verifica endpoint HTMX de paginação e filtragem da tabela de auditoria."""
    session_maker = sessionmaker(bind=db_engine)
    with session_maker() as session:
        subj_repo = SqlAlchemySubjectRepository(session)
        audit_repo = SqlAlchemyReviewAuditRepository(session)

        subj_a = Subject(name="Matéria A", owner_id=test_user.id)
        subj_b = Subject(name="Matéria B", owner_id=test_user.id)
        subj_repo.save(subj_a)
        subj_repo.save(subj_b)

        # 12 logs da Matéria A
        for i in range(12):
            audit_repo.save(
                ReviewAuditLog(
                    user_id=test_user.id,
                    question_id=uuid4(),
                    subject_id=subj_a.id,
                    topic_id=uuid4(),
                    historical_subject_name="Matéria A",
                    historical_topic_name=f"Tema {i}",
                    review_date=date(2026, 10, 7),
                    score=100,
                    level_before=0,
                    level_after=1,
                )
            )
        session.commit()

    # 1. Página 1 do partial
    resp_p1 = client.get("/performance/audit-logs?page=1&page_size=10")
    assert resp_p1.status_code == 200
    p1_html = resp_p1.text
    assert "Página <strong>1</strong> de <strong>2</strong>" in p1_html
    assert "Próxima →" in p1_html

    # 2. Página 2 do partial
    resp_p2 = client.get("/performance/audit-logs?page=2&page_size=10")
    assert resp_p2.status_code == 200
    p2_html = resp_p2.text
    assert "Página <strong>2</strong> de <strong>2</strong>" in p2_html

    # 3. Filtrar por Matéria B (retorna vazio)
    resp_empty = client.get(f"/performance/audit-logs?subject_id={subj_b.id}")
    assert resp_empty.status_code == 200
    assert "Nenhum registro de revisão encontrado" in resp_empty.text


@pytest.mark.integration
def test_performance_export_web_download(
    client: TestClient, db_engine: Any, test_user: User
) -> None:
    """Verifica download de exportação CSV e JSON via web controller."""
    session_maker = sessionmaker(bind=db_engine)
    with session_maker() as session:
        audit_repo = SqlAlchemyReviewAuditRepository(session)
        audit_repo.save(
            ReviewAuditLog(
                user_id=test_user.id,
                question_id=uuid4(),
                subject_id=uuid4(),
                topic_id=uuid4(),
                historical_subject_name="Filosofia",
                historical_topic_name="Ética",
                review_date=date(2026, 10, 7),
                score=100,
                level_before=0,
                level_after=1,
            )
        )
        session.commit()

    # Download CSV
    resp_csv = client.get("/performance/export?format=csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "attachment; filename=" in resp_csv.headers["content-disposition"]
    assert "Filosofia" in resp_csv.text

    # Download JSON
    resp_json = client.get("/performance/export?format=json")
    assert resp_json.status_code == 200
    assert "application/json" in resp_json.headers["content-type"]
    assert "Filosofia" in resp_json.text


@pytest.mark.integration
def test_performance_export_web_invalid_format(client: TestClient) -> None:
    """Verifica erro 400 ao solicitar formato não suportado na exportação web."""
    resp = client.get("/performance/export?format=xml")
    assert resp.status_code == 400


@pytest.mark.integration
def test_audit_logs_htmx_partial_domain_validation_error(db_engine: Any, test_user: User) -> None:
    """Cobre tratamento de DomainValidationError em get_audit_logs_partial."""
    from starlette.requests import Request

    from src.adapters.web.performance_controllers import get_audit_logs_partial

    session_maker = sessionmaker(bind=db_engine)
    with session_maker() as session:
        req = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/performance/audit-logs",
                "headers": [],
            }
        )
        resp = get_audit_logs_partial(request=req, db=session, current_user=test_user, page=0)
        assert resp.status_code == 400
        assert "maior ou igual a 1" in resp.body.decode("utf-8")
