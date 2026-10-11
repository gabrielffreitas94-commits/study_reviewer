"""Testes unitários das entidades de ledger de tokens e avaliação semântica."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.entities import (
    AnswerEvaluationResult,
    TokenLedger,
    TokenTransaction,
)
from src.domain.exceptions import DomainValidationError, InsufficientTokensError


def test_token_ledger_default_and_properties() -> None:
    user_id = uuid4()
    ledger = TokenLedger(user_id=user_id)

    assert ledger.user_id == user_id
    assert ledger.balance == 1000
    assert ledger.held_balance == 0
    assert ledger.available_balance == 1000


def test_token_ledger_invariants() -> None:
    user_id = uuid4()
    with pytest.raises(DomainValidationError, match="O saldo de tokens não pode ser negativo."):
        TokenLedger(user_id=user_id, balance=-1)

    with pytest.raises(
        DomainValidationError, match="O saldo retido de tokens não pode ser negativo."
    ):
        TokenLedger(user_id=user_id, balance=100, held_balance=-5)

    with pytest.raises(
        DomainValidationError, match="O saldo retido não pode exceder o saldo total."
    ):
        TokenLedger(user_id=user_id, balance=100, held_balance=150)


def test_token_ledger_hold_operations() -> None:
    ledger = TokenLedger(user_id=uuid4(), balance=500)

    with pytest.raises(
        DomainValidationError, match="A quantidade para retenção deve ser positiva."
    ):
        ledger.hold(0)

    with pytest.raises(
        DomainValidationError, match="A quantidade para retenção deve ser positiva."
    ):
        ledger.hold(-10)

    with pytest.raises(InsufficientTokensError, match="Saldo insuficiente de tokens"):
        ledger.hold(600)

    ledger.hold(200)
    assert ledger.held_balance == 200
    assert ledger.available_balance == 300

    # Segunda retenção com saldo restante
    ledger.hold(300)
    assert ledger.held_balance == 500
    assert ledger.available_balance == 0

    with pytest.raises(InsufficientTokensError):
        ledger.hold(1)


def test_token_ledger_settle_operations() -> None:
    ledger = TokenLedger(user_id=uuid4(), balance=1000)
    ledger.hold(500)

    with pytest.raises(DomainValidationError, match="Valores de liquidação inválidos."):
        ledger.settle(hold_amount=0, actual_tokens=100)

    with pytest.raises(DomainValidationError, match="Valores de liquidação inválidos."):
        ledger.settle(hold_amount=100, actual_tokens=-1)

    with pytest.raises(
        DomainValidationError,
        match="A retenção a liberar excede o saldo atualmente retido.",
    ):
        ledger.settle(hold_amount=600, actual_tokens=200)

    ledger.settle(hold_amount=500, actual_tokens=220)
    assert ledger.held_balance == 0
    assert ledger.balance == 780
    assert ledger.available_balance == 780


def test_token_ledger_settle_more_than_balance() -> None:
    ledger = TokenLedger(user_id=uuid4(), balance=300)
    ledger.hold(300)
    ledger.settle(hold_amount=300, actual_tokens=400)
    assert ledger.held_balance == 0
    assert ledger.balance == 0


def test_token_ledger_refund_hold() -> None:
    ledger = TokenLedger(user_id=uuid4(), balance=1000)
    ledger.hold(400)

    with pytest.raises(DomainValidationError, match="A quantidade para estorno deve ser positiva."):
        ledger.refund_hold(0)

    with pytest.raises(
        DomainValidationError, match="A quantidade de estorno excede o saldo retido."
    ):
        ledger.refund_hold(500)

    ledger.refund_hold(400)
    assert ledger.held_balance == 0
    assert ledger.balance == 1000
    assert ledger.available_balance == 1000


def test_token_ledger_deposit() -> None:
    ledger = TokenLedger(user_id=uuid4(), balance=200)

    with pytest.raises(DomainValidationError, match="A quantidade de depósito deve ser positiva."):
        ledger.deposit(0)

    with pytest.raises(DomainValidationError, match="A quantidade de depósito deve ser positiva."):
        ledger.deposit(-50)

    ledger.deposit(500)
    assert ledger.balance == 700
    assert ledger.available_balance == 700


def test_token_transaction_valid_and_invariants() -> None:
    user_id = uuid4()
    tx = TokenTransaction(
        user_id=user_id,
        transaction_type="DEPOSIT",
        amount=100,
        reference_id="TEST",
    )
    assert tx.user_id == user_id
    assert tx.transaction_type == "DEPOSIT"
    assert tx.amount == 100
    assert tx.reference_id == "TEST"
    assert isinstance(tx.created_at, datetime)

    with pytest.raises(
        DomainValidationError, match="O montante da transação não pode ser negativo."
    ):
        TokenTransaction(user_id=user_id, transaction_type="DEPOSIT", amount=-1)

    with pytest.raises(DomainValidationError, match="Tipo de transação inválido:"):
        TokenTransaction(user_id=user_id, transaction_type="INVALID_TYPE", amount=100)


def test_answer_evaluation_result_valid_and_invariants() -> None:
    result = AnswerEvaluationResult(
        score=95,
        feedback="Resposta precisa.",
        coverage_score=90,
        accuracy_score=95,
        depth_score=85,
        evidence_quotes=("Evidência 1",),
        tokens_used=180,
        cached_context=True,
        evaluation_mode="AI_TEXT",
    )
    assert result.score == 95
    assert result.feedback == "Resposta precisa."
    assert result.cached_context is True
    assert result.evidence_quotes == ("Evidência 1",)

    with pytest.raises(
        DomainValidationError, match="O score de avaliação deve estar entre 0 e 100."
    ):
        AnswerEvaluationResult(score=-1, feedback="Err")
    with pytest.raises(
        DomainValidationError, match="O score de avaliação deve estar entre 0 e 100."
    ):
        AnswerEvaluationResult(score=101, feedback="Err")

    with pytest.raises(DomainValidationError, match="O coverage_score deve estar entre 0 e 100."):
        AnswerEvaluationResult(score=80, feedback="Ok", coverage_score=-1)

    with pytest.raises(DomainValidationError, match="O accuracy_score deve estar entre 0 e 100."):
        AnswerEvaluationResult(score=80, feedback="Ok", accuracy_score=105)

    with pytest.raises(DomainValidationError, match="O depth_score deve estar entre 0 e 100."):
        AnswerEvaluationResult(score=80, feedback="Ok", depth_score=-5)

    with pytest.raises(DomainValidationError, match="Tokens consumidos não podem ser negativos."):
        AnswerEvaluationResult(score=80, feedback="Ok", tokens_used=-10)

    with pytest.raises(DomainValidationError, match="Feedback de avaliação não pode ser vazio."):
        AnswerEvaluationResult(score=80, feedback="   ")

    with pytest.raises(DomainValidationError, match="Modo de avaliação inválido:"):
        AnswerEvaluationResult(score=80, feedback="Ok", evaluation_mode="INVALID_MODE")
