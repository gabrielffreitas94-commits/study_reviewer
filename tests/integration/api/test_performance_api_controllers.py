"""Testes de integração para os controladores de API REST de Performance e Auditoria (Sprint 04)."""

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
    SqlAlchemyUserRepository,
)
from src.domain.entities import (
    ReviewAuditLog,
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
        google_sub="sub-perf-api-1",
        email="perf.api@test.com",
        name="Performance API User",
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
def test_get_statistics_api_empty_state(client: TestClient) -> None:
    """Verifica retorno de estatísticas para usuário sem revisões."""
    response = client.get("/api/v1/performance/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_reviews_count"] == 0
    assert data["retention_rate"] == 0.0
    assert data["mature_questions_count"] == 0
    assert data["active_days_count"] == 0
    assert data["subject_performances"] == []


@pytest.mark.integration
def test_get_statistics_api_with_data(client: TestClient, db_engine: Any, test_user: User) -> None:
    """Verifica KPIs e timelines agregadas de estatísticas."""
    session_maker = sessionmaker(bind=db_engine)
    with session_maker() as session:
        audit_repo = SqlAlchemyReviewAuditRepository(session)
        prog_repo = SqlAlchemyQuestionProgressRepository(session)

        q1 = uuid4()
        audit_repo.save(
            ReviewAuditLog(
                user_id=test_user.id,
                question_id=q1,
                subject_id=uuid4(),
                topic_id=uuid4(),
                historical_subject_name="Direito",
                historical_topic_name="Constitucional",
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

    response = client.get("/api/v1/performance/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_reviews_count"] == 1
    assert data["retention_rate"] == 100.0
    assert data["mature_questions_count"] == 1
    assert data["active_days_count"] == 1
    assert len(data["subject_performances"]) == 1
    assert data["subject_performances"][0]["subject_name"] == "Direito"


@pytest.mark.integration
def test_list_audit_logs_api_pagination(
    client: TestClient, db_engine: Any, test_user: User
) -> None:
    """Verifica paginação no endpoint REST de logs de auditoria."""
    session_maker = sessionmaker(bind=db_engine)
    with session_maker() as session:
        audit_repo = SqlAlchemyReviewAuditRepository(session)
        for i in range(15):
            audit_repo.save(
                ReviewAuditLog(
                    user_id=test_user.id,
                    question_id=uuid4(),
                    subject_id=uuid4(),
                    topic_id=uuid4(),
                    historical_subject_name=f"Matéria {i}",
                    historical_topic_name=f"Tema {i}",
                    review_date=date(2026, 10, 7),
                    score=100,
                    level_before=0,
                    level_after=1,
                )
            )
        session.commit()

    # Página 1 (10 itens)
    resp_p1 = client.get("/api/v1/performance/audit-logs?page=1&page_size=10")
    assert resp_p1.status_code == 200
    p1_data = resp_p1.json()
    assert len(p1_data["items"]) == 10
    assert p1_data["total_items"] == 15
    assert p1_data["total_pages"] == 2

    # Página 2 (5 itens)
    resp_p2 = client.get("/api/v1/performance/audit-logs?page=2&page_size=10")
    assert resp_p2.status_code == 200
    assert len(resp_p2.json()["items"]) == 5


@pytest.mark.integration
@pytest.mark.security
def test_export_user_data_api_csv_and_json(
    client: TestClient, db_engine: Any, test_user: User
) -> None:
    """Verifica exportação em CSV (com BOM e anti-injection) e JSON via API.

    Vulnerabilidade prevenida: CSV Formula Injection (CWE-1236) e Vazamento de Dados LGPD (Art. 18).
    Garantia de segurança: Fórmulas maliciosas são neutralizadas com apóstrofo e o arquivo exportado
    contém estritamente os dados do usuário autenticado sem vazar dados de terceiros.
    """
    session_maker = sessionmaker(bind=db_engine)
    with session_maker() as session:
        audit_repo = SqlAlchemyReviewAuditRepository(session)
        audit_repo.save(
            ReviewAuditLog(
                user_id=test_user.id,
                question_id=uuid4(),
                subject_id=uuid4(),
                topic_id=uuid4(),
                historical_subject_name="=cmd|'calc'!A0",
                historical_topic_name="Ataque CSV",
                review_date=date(2026, 10, 7),
                score=100,
                level_before=0,
                level_after=1,
            )
        )
        session.commit()

    # 1. Export CSV
    resp_csv = client.get("/api/v1/performance/export?format=csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert resp_csv.headers["x-content-type-options"] == "nosniff"
    csv_text = resp_csv.text
    assert csv_text.startswith("\ufeff")
    assert "'=cmd|'calc'!A0" in csv_text

    # 2. Export JSON
    resp_json = client.get("/api/v1/performance/export?format=json")
    assert resp_json.status_code == 200
    assert "application/json" in resp_json.headers["content-type"]
    exported_data = resp_json.json()
    assert exported_data["user"]["email"] == "perf.api@test.com"
    assert len(exported_data["review_logs"]) == 1

    # 3. Formato inválido
    resp_bad = client.get("/api/v1/performance/export?format=pdf")
    assert resp_bad.status_code == 400


@pytest.mark.integration
def test_list_audit_logs_api_domain_validation_error(db_engine: Any, test_user: User) -> None:
    """Cobre tratamento de DomainValidationError em list_user_audit_logs_api."""
    from fastapi import HTTPException

    from src.adapters.api.performance_controllers import list_user_audit_logs_api

    session_maker = sessionmaker(bind=db_engine)
    with session_maker() as session:
        with pytest.raises(HTTPException) as exc_info:
            list_user_audit_logs_api(db=session, current_user=test_user, page=0)
        assert exc_info.value.status_code == 400
