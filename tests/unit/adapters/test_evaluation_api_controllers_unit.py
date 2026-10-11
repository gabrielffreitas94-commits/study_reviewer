"""Testes unitários para controladores de avaliação e tokens (Sprint 08)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.adapters.api.evaluation_controllers import (
    DepositTokensRequest,
    EvaluateAnswerRequest,
    deposit_user_tokens,
    evaluate_text_answer,
    get_user_token_balance,
    list_user_token_transactions,
)
from src.application.dto.evaluation_dto import (
    TokenTransactionDTO,
    UserTokenBalanceDTO,
)
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    EvaluationServiceError,
    InsufficientTokensError,
    QuestionNotDueError,
    QuestionNotFoundError,
    ResourceOwnershipError,
)


@pytest.fixture
def mock_user() -> User:
    return User(
        id=uuid4(),
        google_sub="sub-unit-eval",
        email="eval.unit@test.local",
        name="Unit Eval User",
    )


def test_evaluate_text_answer_controller_exceptions(mock_user: User) -> None:
    db = MagicMock()
    q_id = uuid4()
    req = EvaluateAnswerRequest(student_answer="Resposta teste")

    # 1. InsufficientTokensError -> 402
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateStudentAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=InsufficientTokensError("Saldo insuficiente"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_text_answer(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 402

    # 2. DomainValidationError -> 400
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateStudentAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=DomainValidationError("Entrada inválida"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_text_answer(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 400

    # 3. QuestionNotDueError -> 400
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateStudentAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=QuestionNotDueError("Não vencida"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_text_answer(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 400

    # 4. ResourceOwnershipError -> 403
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateStudentAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=ResourceOwnershipError("Proibido"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_text_answer(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 403

    # 5. QuestionNotFoundError -> 404
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateStudentAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=QuestionNotFoundError("Pergunta não encontrada"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_text_answer(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 404

    # 6. EntityNotFoundError -> 404
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateStudentAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=EntityNotFoundError("Tema não encontrado"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_text_answer(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 404

    # 7. EvaluationServiceError -> 503
    with patch(
        "src.adapters.api.evaluation_controllers.EvaluateStudentAnswerUseCase.execute",
        new_callable=AsyncMock,
        side_effect=EvaluationServiceError("Serviço indisponível"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(evaluate_text_answer(q_id, req, mock_user, db))
        assert exc_info.value.status_code == 503


def test_deposit_user_tokens_domain_validation_exception(mock_user: User) -> None:
    db = MagicMock()
    req = DepositTokensRequest(amount=100)

    with patch(
        "src.adapters.api.evaluation_controllers.DepositTokensUseCase.execute",
        side_effect=DomainValidationError("Erro de validação do domínio"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            deposit_user_tokens(req, mock_user, db)
        assert exc_info.value.status_code == 400
        assert "Erro de validação do domínio" in str(exc_info.value.detail)


def test_get_user_token_balance_unit(mock_user: User) -> None:
    db = MagicMock()
    with patch(
        "src.adapters.api.evaluation_controllers.GetUserTokenBalanceUseCase.execute",
        return_value=UserTokenBalanceDTO(
            user_id=mock_user.id,
            balance=1500,
            held_balance=300,
            available_balance=1200,
        ),
    ):
        result = get_user_token_balance(mock_user, db)
        assert result["balance"] == 1500
        assert result["held_balance"] == 300
        assert result["available_balance"] == 1200


def test_list_user_token_transactions_unit(mock_user: User) -> None:
    db = MagicMock()
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    with patch(
        "src.adapters.api.evaluation_controllers.ListTokenTransactionsUseCase.execute",
        return_value=[
            TokenTransactionDTO(
                id=uuid4(),
                transaction_type="DEPOSIT",
                amount=500,
                reference_id="PURCHASE",
                created_at=now,
            )
        ],
    ):
        results = list_user_token_transactions(limit=10, current_user=mock_user, db=db)
        assert len(results) == 1
        assert results[0]["transaction_type"] == "DEPOSIT"
        assert results[0]["amount"] == 500
