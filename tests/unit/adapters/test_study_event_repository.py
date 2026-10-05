"""Testes unitários para o SqlAlchemyStudyEventRepository."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.adapters.persistence.repositories import SqlAlchemyStudyEventRepository


@pytest.mark.unit
def test_study_event_repository_bulk_insert_empty() -> None:
    """bulk_insert com lista vazia retorna 0 sem executar query."""
    mock_session = MagicMock()
    repo = SqlAlchemyStudyEventRepository(mock_session)
    assert repo.bulk_insert([]) == 0
    mock_session.execute.assert_not_called()


@pytest.mark.unit
def test_study_event_repository_bulk_insert_postgresql_dialect() -> None:
    """Verifica ramo do dialeto postgresql no bulk_insert com ON CONFLICT DO NOTHING."""
    mock_session = MagicMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_session.get_bind.return_value = mock_bind
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session.execute.return_value = mock_result

    repo = SqlAlchemyStudyEventRepository(mock_session)
    events = [
        {
            "id": uuid4(),
            "reviewed_at": datetime.now(UTC),
            "user_id": uuid4(),
            "card_id": uuid4(),
            "session_id": uuid4(),
            "status": "viewed",
            "device_id": "pg-test",
        }
    ]
    res = repo.bulk_insert(events)
    assert res == 1
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()
