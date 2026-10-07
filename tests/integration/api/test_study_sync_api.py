"""Testes de integração e segurança para o endpoint de sincronização de respostas (Seção 9.4)."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.adapters.persistence.models import (
    FlashcardModel,
    FlashcardPoolSessionModel,
    SubjectModel,
    TopicModel,
)
from src.adapters.persistence.repositories import (
    SqlAlchemyStudyEventRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import User
from src.infrastructure.database import Base, get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.security.rate_limiter import reset_rate_limits
from src.infrastructure.web.app import app


@pytest.fixture(autouse=True)
def _clear_rate_limiter() -> Generator[None]:
    """Limpa a janela deslizante de rate limiting antes e depois de cada teste."""
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def test_user() -> User:
    """Usuário autenticado principal para testes de estudo."""
    return User(
        id=uuid4(),
        google_sub="test-sub-sync-user-1",
        email="sync.user1@studyreviewer.local",
        name="Estudante Sync 1",
    )


@pytest.fixture
def other_user() -> User:
    """Outro usuário para testes de isolamento de tenant e anti-IDOR."""
    return User(
        id=uuid4(),
        google_sub="test-sub-sync-user-2",
        email="sync.user2@studyreviewer.local",
        name="Estudante Sync 2",
    )


@pytest.fixture
def db_session() -> Generator[Session]:
    """Cria uma sessão SQLite isolada em memória para cada teste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session, test_user: User, other_user: User) -> Generator[TestClient]:
    """Cria TestClient com injeção de dependências e usuários persistidos no banco."""
    user_repo = SqlAlchemyUserRepository(db_session)
    user_repo.save(test_user)
    user_repo.save(other_user)

    def override_get_db() -> Generator[Session]:
        yield db_session

    def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _seed_study_session(
    session: Session, user: User
) -> tuple[FlashcardPoolSessionModel, list[FlashcardModel]]:
    """Auxiliar para semear matéria, tema, cards e sessão de estudo ativa."""
    sub = SubjectModel(id=uuid4(), owner_id=user.id, name="Matéria Teste", is_public=False)
    session.add(sub)
    session.flush()

    topic = TopicModel(id=uuid4(), subject_id=sub.id, name="Tema Teste")
    session.add(topic)
    session.flush()

    cards = [
        FlashcardModel(
            id=uuid4(),
            front=f"Pergunta {i}",
            back=f"Resposta {i}",
            position=100 * (i + 1),
            topics=[topic],
        )
        for i in range(3)
    ]
    for c in cards:
        session.add(c)
    session.flush()

    study_session = FlashcardPoolSessionModel(
        id=uuid4(),
        user_id=user.id,
        subject_id_filter=sub.id,
        topic_id_filter=topic.id,
        current_position=cards[0].position,
        round_number=1,
        current_index=0,
        card_queue=[c.id for c in cards],
    )
    session.add(study_session)
    session.commit()
    return study_session, cards


@pytest.mark.security
@pytest.mark.integration
def test_sync_answers_anti_idor_prevention(
    client: TestClient, db_session: Session, test_user: User, other_user: User
) -> None:
    """Vulnerabilidade prevenida: CWE-639 Insecure Direct Object References (IDOR).

    Garantia de segurança: Assegura que um usuário autenticado não pode ingerir
    eventos ou alterar o estado da sessão de estudo de outro estudante, retornando HTTP 403.
    """
    # Cria sessão pertencente ao outro usuário
    other_session, other_cards = _seed_study_session(db_session, other_user)

    payload = {
        "session_id": str(other_session.id),
        "events": [
            {
                "id": str(uuid4()),
                "card_id": str(other_cards[0].id),
                "reviewed_at": datetime.now(UTC).isoformat(),
                "status": "viewed",
                "device_id": "attacker-dev",
            }
        ],
        "batch_index": 1,
    }

    # Usuário atual (test_user) tenta enviar eventos para a sessão de other_user
    response = client.post("/api/v1/study/sync-answers", json=payload)
    assert response.status_code == 403
    assert "Acesso negado: a sessão informada pertence a outro usuário" in response.text


@pytest.mark.security
@pytest.mark.integration
def test_sync_answers_rate_limit_exceeded(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Vulnerabilidade prevenida: OWASP A04 Rate Limiting & Denial of Service (DoS).

    Garantia de segurança: Restringe a sincronização a no máximo 20 requisições por minuto
    por usuário autenticado, bloqueando excedentes com HTTP 429 Too Many Requests.
    """
    study_session, cards = _seed_study_session(db_session, test_user)

    payload = {
        "session_id": str(study_session.id),
        "events": [
            {
                "id": str(uuid4()),
                "card_id": str(cards[0].id),
                "reviewed_at": datetime.now(UTC).isoformat(),
                "status": "viewed",
                "device_id": "test-dev",
            }
        ],
        "batch_index": 1,
    }

    # Executa 20 requisições com sucesso
    for _ in range(20):
        resp = client.post("/api/v1/study/sync-answers", json=payload)
        assert resp.status_code == 200

    # A 21ª requisição deve ser sumariamente bloqueada pelo rate limiter
    resp_blocked = client.post("/api/v1/study/sync-answers", json=payload)
    assert resp_blocked.status_code == 429
    assert "Limite de taxa excedido" in resp_blocked.text
    assert resp_blocked.headers.get("retry-after") == "60"


@pytest.mark.security
@pytest.mark.integration
def test_sync_answers_future_clock_skew_rejected(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Vulnerabilidade prevenida: Manipulação temporal maliciosa e metric poisoning.

    Garantia de segurança: Rejeita eventos com timestamps adulterados no futuro
    além da tolerância máxima aceitável de 60 segundos com HTTP 422.
    """
    study_session, cards = _seed_study_session(db_session, test_user)
    future_time = datetime.now(UTC) + timedelta(minutes=10)

    payload = {
        "session_id": str(study_session.id),
        "events": [
            {
                "id": str(uuid4()),
                "card_id": str(cards[0].id),
                "reviewed_at": future_time.isoformat(),
                "status": "viewed",
                "device_id": "time-travel-dev",
            }
        ],
        "batch_index": 1,
    }

    response = client.post("/api/v1/study/sync-answers", json=payload)
    assert response.status_code == 422
    assert "Timestamp inválido" in response.text


@pytest.mark.security
@pytest.mark.integration
def test_sync_answers_expired_offline_batch_rejected(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Vulnerabilidade prevenida: Replay attacks e ingestão de dados obsoletos.

    Garantia de segurança: Rejeita lotes offline defasados há mais de 30 dias
    com HTTP 422 para preservar integridade analítica e prevenir ataques de repetição.
    """
    study_session, cards = _seed_study_session(db_session, test_user)
    expired_time = datetime.now(UTC) - timedelta(days=32)

    payload = {
        "session_id": str(study_session.id),
        "events": [
            {
                "id": str(uuid4()),
                "card_id": str(cards[0].id),
                "reviewed_at": expired_time.isoformat(),
                "status": "viewed",
                "device_id": "old-dev",
            }
        ],
        "batch_index": 1,
    }

    response = client.post("/api/v1/study/sync-answers", json=payload)
    assert response.status_code == 422
    assert "Timestamp expirado" in response.text


@pytest.mark.security
@pytest.mark.integration
def test_sync_answers_idempotent_deduplication(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Vulnerabilidade prevenida: Corrupção de métricas por duplicação acidental de rede.

    Garantia de segurança: Assegura que o reenvio idempotente do mesmo evento não gera
    duplicidade de linhas na tabela de eventos de estudo (ON CONFLICT DO NOTHING).
    """
    study_session, cards = _seed_study_session(db_session, test_user)
    event_id = uuid4()
    reviewed_at = datetime.now(UTC).isoformat()

    payload = {
        "session_id": str(study_session.id),
        "events": [
            {
                "id": str(event_id),
                "card_id": str(cards[0].id),
                "reviewed_at": reviewed_at,
                "status": "viewed",
                "device_id": "test-dev",
            }
        ],
        "batch_index": 1,
    }

    # Primeiro envio
    resp1 = client.post("/api/v1/study/sync-answers", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["synced_count"] == 1

    # Reenvio idêntico
    resp2 = client.post("/api/v1/study/sync-answers", json=payload)
    assert resp2.status_code == 200

    # Verifica no banco que apenas 1 registro foi persistido
    event_repo = SqlAlchemyStudyEventRepository(db_session)
    events = event_repo.list_by_user(test_user.id)
    assert len(events) == 1
    assert events[0]["card_id"] == cards[0].id


@pytest.mark.security
@pytest.mark.integration
def test_sync_answers_payload_too_large(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Vulnerabilidade prevenida: Exaustão de memória e DoS via payload excessivo.

    Garantia de segurança: Intercepta e rejeita requisições com corpo superior
    a 256 KB retornando HTTP 413 Payload Too Large antes de parsear dados.
    """
    study_session, cards = _seed_study_session(db_session, test_user)

    # Cria payload com cabeçalho simulando tamanho superior a 256 KB
    payload = {
        "session_id": str(study_session.id),
        "events": [
            {
                "id": str(uuid4()),
                "card_id": str(cards[0].id),
                "reviewed_at": datetime.now(UTC).isoformat(),
                "status": "viewed",
                "device_id": "dev",
            }
        ],
        "batch_index": 1,
    }

    # Envia com cabeçalho Content-Length excedendo 256 KB (262145 bytes)
    response = client.post(
        "/api/v1/study/sync-answers",
        json=payload,
        headers={"Content-Length": "300000"},
    )
    assert response.status_code == 413
    assert "Payload Too Large" in response.text


@pytest.mark.security
@pytest.mark.integration
def test_sync_answers_card_not_in_session_queue(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Vulnerabilidade prevenida: Dessincronização de fila e adulteração de card ID.

    Garantia de segurança: Rejeita respostas associadas a flashcards que não fazem
    parte da fila oficial da sessão ativa do usuário com HTTP 422.
    """
    study_session, cards = _seed_study_session(db_session, test_user)
    foreign_card_id = uuid4()

    payload = {
        "session_id": str(study_session.id),
        "events": [
            {
                "id": str(uuid4()),
                "card_id": str(foreign_card_id),
                "reviewed_at": datetime.now(UTC).isoformat(),
                "status": "viewed",
                "device_id": "test-dev",
            }
        ],
        "batch_index": 1,
    }

    response = client.post("/api/v1/study/sync-answers", json=payload)
    assert response.status_code == 403
    assert "não está autorizado para esta sessão de estudo" in response.text


@pytest.mark.security
@pytest.mark.integration
def test_lgpd_anonymize_user_events(db_session: Session, test_user: User) -> None:
    """Vulnerabilidade prevenida: Retenção indevida de dados pessoais (LGPD Art. 18, VI).

    Garantia de segurança: Desvincula irreversivelmente user_id e device_id de todos os eventos
    de estudo do titular, mantendo registros puramente anonimizados sob a base do Art. 16, IV.
    """
    study_session, cards = _seed_study_session(db_session, test_user)
    event_repo = SqlAlchemyStudyEventRepository(db_session)

    # Insere eventos para o usuário
    events_to_insert = [
        {
            "id": uuid4(),
            "reviewed_at": datetime.now(UTC),
            "user_id": test_user.id,
            "card_id": cards[0].id,
            "session_id": study_session.id,
            "status": "viewed",
            "device_id": "desktop-personal",
        },
        {
            "id": uuid4(),
            "reviewed_at": datetime.now(UTC),
            "user_id": test_user.id,
            "card_id": cards[1].id,
            "session_id": study_session.id,
            "status": "completed",
            "device_id": "desktop-personal",
        },
    ]
    inserted = event_repo.bulk_insert(events_to_insert)
    assert inserted == 2

    # Executa a rotina mandatória de anonimização da LGPD
    anonymized_count = event_repo.anonymize_user_events(test_user.id)
    assert anonymized_count == 2

    # Verifica que a listagem por user_id não encontra nenhum registro
    user_events = event_repo.list_by_user(test_user.id)
    assert len(user_events) == 0

    # Eventos anonimizados permanecem no banco para calibração estatística
    from sqlalchemy import select

    from src.adapters.persistence.models import StudyEventModel

    raw_events = db_session.scalars(select(StudyEventModel)).all()
    assert len(raw_events) == 2
    for rev in raw_events:
        assert rev.user_id is None
        assert rev.device_id is None


@pytest.mark.security
@pytest.mark.integration
def test_sync_answers_session_not_found(client: TestClient) -> None:
    """Vulnerabilidade prevenida: Referência insegura a recursos inexistentes.

    Garantia de segurança: Retorna HTTP 404 quando o session_id fornecido não existe
    no repositório de sessões ativas do sistema.
    """
    payload = {
        "session_id": str(uuid4()),
        "events": [
            {
                "id": str(uuid4()),
                "card_id": str(uuid4()),
                "reviewed_at": datetime.now(UTC).isoformat(),
                "status": "viewed",
                "device_id": "dev",
            }
        ],
        "batch_index": 1,
    }
    resp = client.post("/api/v1/study/sync-answers", json=payload)
    assert resp.status_code == 404
    assert "Sessão de estudo não encontrada" in resp.text


@pytest.mark.unit
def test_sync_answers_use_case_direct_validations(db_session: Session) -> None:
    """Testa validações de domínio diretamente no caso de uso SyncStudyAnswersUseCase."""
    from src.adapters.persistence.repositories import (
        SqlAlchemySessionRepository,
        SqlAlchemyStudyEventRepository,
    )
    from src.application.dto.study_dto import StudyEventDTO, SyncStudyBatchDTO
    from src.application.use_cases.sync_study_answers_use_case import SyncStudyAnswersUseCase
    from src.domain.exceptions import DomainValidationError

    event_repo = SqlAlchemyStudyEventRepository(db_session)
    session_repo = SqlAlchemySessionRepository(db_session)
    use_case = SyncStudyAnswersUseCase(event_repo, session_repo)

    # 1. Validação de lote vazio
    with pytest.raises(DomainValidationError, match="O lote deve conter entre 1 e 100 eventos"):
        use_case.execute(
            SyncStudyBatchDTO(session_id=uuid4(), events=[]),
            user_id=uuid4(),
        )

    # 2. Validação de status inválido
    dummy_user = User(id=uuid4(), google_sub="sub", email="e@e.com", name="N")
    study_session, cards = _seed_study_session(db_session, dummy_user)
    with pytest.raises(DomainValidationError, match="Status inválido"):
        use_case.execute(
            SyncStudyBatchDTO(
                session_id=study_session.id,
                events=[
                    StudyEventDTO(
                        id=uuid4(),
                        card_id=cards[0].id,
                        reviewed_at=datetime.now(UTC),
                        status="invalid_status",
                    )
                ],
            ),
            user_id=study_session.user_id,
        )

    # 3. Validação de fila de sessão vazia
    empty_session = FlashcardPoolSessionModel(
        id=uuid4(),
        user_id=dummy_user.id,
        current_position=100,
        round_number=1,
        current_index=0,
        card_queue=[],
    )
    db_session.add(empty_session)
    db_session.commit()

    with pytest.raises(DomainValidationError, match="não possui cards em sua fila ativa"):
        use_case.execute(
            SyncStudyBatchDTO(
                session_id=empty_session.id,
                events=[
                    StudyEventDTO(
                        id=uuid4(),
                        card_id=uuid4(),
                        reviewed_at=datetime.now(UTC),
                        status="viewed",
                    )
                ],
            ),
            user_id=dummy_user.id,
        )


@pytest.mark.unit
def test_sync_answers_api_direct_call_fallback_event_repo(
    db_session: Session, test_user: User
) -> None:
    """Verifica que sync_answers_api resolve get_study_event_repo quando event_repo é None."""
    from unittest.mock import MagicMock

    from src.adapters.api.controllers import (
        StudyEventItemRequest,
        SyncAnswersPayload,
        sync_answers_api,
    )

    study_session, cards = _seed_study_session(db_session, test_user)
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None

    payload = SyncAnswersPayload(
        session_id=study_session.id,
        events=[
            StudyEventItemRequest(
                id=uuid4(),
                card_id=cards[0].id,
                reviewed_at=datetime.now(UTC),
                status="viewed",
            )
        ],
    )
    res = sync_answers_api(
        request=mock_request,
        payload=payload,
        db=db_session,
        current_user=test_user,
        event_repo=None,  # type: ignore[arg-type]
    )
    assert res.status == "ok"
    assert res.synced_count == 1


@pytest.mark.integration
def test_sync_answers_api_with_correlation_id_telemetry(
    client: TestClient, db_session: Session, test_user: User, caplog: pytest.LogCaptureFixture
) -> None:
    """Verifica se o cabeçalho X-Correlation-ID é capturado e registrado na telemetria estruturada."""
    import logging

    study_session, cards = _seed_study_session(db_session, test_user)
    correlation_id = f"sync-corr-{uuid4()}"
    payload = {
        "session_id": str(study_session.id),
        "events": [
            {
                "id": str(uuid4()),
                "card_id": str(cards[0].id),
                "reviewed_at": datetime.now(UTC).isoformat(),
                "status": "viewed",
                "device_id": "test-device-uuid-123",
            }
        ],
        "batch_index": 1,
    }
    with caplog.at_level(logging.INFO):
        resp = client.post(
            "/api/v1/study/sync-answers",
            json=payload,
            headers={"X-Correlation-ID": correlation_id},
        )
    assert resp.status_code == 200
    assert any(
        getattr(record, "correlation_id", None) == correlation_id
        or correlation_id in record.message
        for record in caplog.records
    )

