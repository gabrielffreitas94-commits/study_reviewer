"""Testes unitários e de conformidade do repositório DynamoDbStudyEventRepository."""

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import boto3
import pytest
from moto import mock_aws

from src.adapters.persistence.dynamodb_study_event_repository import (
    DynamoDbStudyEventRepository,
)


@pytest.fixture
def mock_dynamodb_table() -> Generator[tuple[Any, Any]]:
    """Cria uma tabela mock no DynamoDB via Moto para testes unitários isolados."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="study_events_test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield table, dynamodb


@pytest.mark.unit
def test_dynamodb_study_event_repository_bulk_insert_empty(
    mock_dynamodb_table: tuple[Any, Any],
) -> None:
    """bulk_insert com lista vazia retorna 0 sem efetuar chamadas ao DynamoDB."""
    _, dynamodb = mock_dynamodb_table
    repo = DynamoDbStudyEventRepository(
        table_name="study_events_test",
        region_name="us-east-1",
        dynamodb_resource=dynamodb,
    )
    assert repo.bulk_insert([]) == 0


@pytest.mark.unit
def test_dynamodb_study_event_repository_bulk_insert_and_list(
    mock_dynamodb_table: tuple[Any, Any],
) -> None:
    """Verifica inserção em lote no DynamoDB e recuperação cronológica reversa."""
    table, dynamodb = mock_dynamodb_table
    repo = DynamoDbStudyEventRepository(
        table_name="study_events_test",
        region_name="us-east-1",
        ttl_days=30,
        dynamodb_resource=dynamodb,
    )

    user_id = uuid4()
    session_id = uuid4()
    card_1 = uuid4()
    card_2 = uuid4()

    t1 = datetime(2026, 10, 5, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 10, 5, 10, 5, 0, tzinfo=UTC)

    events = [
        {
            "id": uuid4(),
            "reviewed_at": t1,
            "user_id": user_id,
            "card_id": card_1,
            "session_id": session_id,
            "status": "viewed",
            "device_id": "mobile-app",
        },
        {
            "id": uuid4(),
            "reviewed_at": t2,
            "user_id": user_id,
            "card_id": card_2,
            "session_id": session_id,
            "status": "completed",
            "device_id": "mobile-app",
        },
        {
            "id": uuid4(),
            "reviewed_at": t1.isoformat(),  # formato string ISO
            "user_id": None,  # anônimo
            "card_id": uuid4(),
            "session_id": session_id,
            "status": "viewed",
        },
    ]

    inserted = repo.bulk_insert(events)
    assert inserted == 3

    # Consulta por usuário
    user_events = repo.list_by_user(user_id, limit=10)
    assert len(user_events) == 2
    # Ordenação reversa (t2 mais recente primeiro)
    assert user_events[0]["reviewed_at"] == t2
    assert user_events[0]["status"] == "completed"
    assert user_events[0]["card_id"] == card_2
    assert user_events[1]["reviewed_at"] == t1
    assert user_events[1]["status"] == "viewed"


@pytest.mark.security
@pytest.mark.unit
def test_dynamodb_study_event_repository_anonymize_user_events_lgpd(
    mock_dynamodb_table: tuple[Any, Any],
) -> None:
    """Vulnerabilidade prevenida: Retenção indevida de dados pessoais pós-exclusão de conta.

    Garantia de segurança: Assegura que eventos sejam irreversivelmente desvinculados do usuário
    e movidos para a partição anônima no DynamoDB em conformidade com o Art. 16, IV da LGPD.
    """
    table, dynamodb = mock_dynamodb_table
    repo = DynamoDbStudyEventRepository(
        table_name="study_events_test",
        region_name="us-east-1",
        dynamodb_resource=dynamodb,
    )

    user_id = uuid4()
    session_id = uuid4()
    event_id = uuid4()

    repo.bulk_insert(
        [
            {
                "id": event_id,
                "reviewed_at": datetime.now(UTC),
                "user_id": user_id,
                "card_id": uuid4(),
                "session_id": session_id,
                "status": "completed",
                "device_id": "secret-device",
            }
        ]
    )

    # Verifica que usuário possui 1 evento antes da anonimização
    assert len(repo.list_by_user(user_id)) == 1

    # Executa anonimização
    count = repo.anonymize_user_events(user_id)
    assert count == 1

    # Após anonimização, busca pelo user_id não encontra nada
    assert len(repo.list_by_user(user_id)) == 0

    # Busca quando usuário não possui eventos
    assert repo.anonymize_user_events(uuid4()) == 0


@pytest.mark.unit
def test_dynamodb_study_event_repository_default_resource() -> None:
    """Verifica instanciação com recursos padrões do boto3."""
    with mock_aws():
        repo = DynamoDbStudyEventRepository(
            table_name="default_table",
            region_name="us-east-1",
        )
        assert repo._table_name == "default_table"
        assert repo._region == "us-east-1"
