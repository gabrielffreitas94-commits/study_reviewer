"""Controladores REST para Avaliação Semântica com IA e Ledger de Tokens (Sprint 08)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.ai.gemini_adapters import GeminiAnswerEvaluationAdapter
from src.adapters.persistence.repositories import (
    SqlAlchemyKnowledgeChunkRepository,
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyReviewAuditRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTokenLedgerRepository,
    SqlAlchemyTopicRepository,
)
from src.application.dto.evaluation_dto import (
    DepositTokensInputDTO,
    EvaluateAnswerInputDTO,
)
from src.application.use_cases.evaluation_use_cases import (
    DepositTokensUseCase,
    EvaluateStudentAnswerUseCase,
    GetUserTokenBalanceUseCase,
    ListTokenTransactionsUseCase,
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
from src.infrastructure.clock import SystemClockService
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import get_current_user

api_evaluation_router = APIRouter(prefix="/api/v1", tags=["AI Evaluation & Token Metering"])


class EvaluateAnswerRequest(BaseModel):
    """Payload para submissão de resposta aberta para avaliação por IA."""

    student_answer: str = Field(..., min_length=1, max_length=10000)


class DepositTokensRequest(BaseModel):
    """Payload para recarga de créditos de tokens."""

    amount: int = Field(..., gt=0, le=1_000_000)


@api_evaluation_router.post(
    "/questions/{question_id}/evaluate-text",
    status_code=status.HTTP_200_OK,
    summary="Avaliar resposta dissertativa com IA aterrada e atualizar repetição espaçada",
)
async def evaluate_text_answer(
    question_id: UUID,
    payload: EvaluateAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Avalia semanticamente a resposta com hold atômico e liquidação de tokens."""
    clock = SystemClockService()
    use_case = EvaluateStudentAnswerUseCase(
        question_repo=SqlAlchemyQuestionRepository(db),
        topic_repo=SqlAlchemyTopicRepository(db),
        subject_repo=SqlAlchemySubjectRepository(db),
        progress_repo=SqlAlchemyQuestionProgressRepository(db),
        chunk_repo=SqlAlchemyKnowledgeChunkRepository(db),
        ledger_repo=SqlAlchemyTokenLedgerRepository(db),
        evaluation_service=GeminiAnswerEvaluationAdapter(),
        clock=clock,
        audit_repo=SqlAlchemyReviewAuditRepository(db),
        uow=db,
    )

    try:
        result = await use_case.execute(
            dto=EvaluateAnswerInputDTO(
                question_id=question_id,
                student_answer=payload.student_answer,
            ),
            user_id=current_user.id,
        )
        return {
            "question_id": str(result.question_id),
            "score": result.score,
            "feedback": result.feedback,
            "coverage_score": result.coverage_score,
            "accuracy_score": result.accuracy_score,
            "depth_score": result.depth_score,
            "evidence_quotes": result.evidence_quotes,
            "level_before": result.level_before,
            "level_after": result.level_after,
            "next_review_date": result.next_review_date.isoformat(),
            "tokens_deducted": result.tokens_deducted,
            "remaining_token_balance": result.remaining_token_balance,
            "evaluation_mode": result.evaluation_mode,
        }
    except InsufficientTokensError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
        ) from e
    except (DomainValidationError, QuestionNotDueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ResourceOwnershipError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except (QuestionNotFoundError, EntityNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except EvaluationServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e


@api_evaluation_router.get(
    "/users/me/token-balance",
    status_code=status.HTTP_200_OK,
    summary="Consultar saldo atual de tokens do estudante",
)
def get_user_token_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna saldo total, retido e disponível no ledger de tokens."""
    use_case = GetUserTokenBalanceUseCase(
        ledger_repo=SqlAlchemyTokenLedgerRepository(db),
    )
    balance_dto = use_case.execute(user_id=current_user.id)
    return {
        "user_id": str(balance_dto.user_id),
        "balance": balance_dto.balance,
        "held_balance": balance_dto.held_balance,
        "available_balance": balance_dto.available_balance,
    }


@api_evaluation_router.post(
    "/users/me/tokens/deposit",
    status_code=status.HTTP_200_OK,
    summary="Adicionar créditos de tokens à conta",
)
def deposit_user_tokens(
    payload: DepositTokensRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Credita tokens no ledger do usuário."""
    use_case = DepositTokensUseCase(
        ledger_repo=SqlAlchemyTokenLedgerRepository(db),
        uow=db,
    )
    try:
        balance_dto = use_case.execute(
            dto=DepositTokensInputDTO(amount=payload.amount),
            user_id=current_user.id,
        )
        return {
            "user_id": str(balance_dto.user_id),
            "balance": balance_dto.balance,
            "held_balance": balance_dto.held_balance,
            "available_balance": balance_dto.available_balance,
        }
    except DomainValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@api_evaluation_router.get(
    "/users/me/tokens/transactions",
    status_code=status.HTTP_200_OK,
    summary="Listar extrato de transações de tokens",
)
def list_user_token_transactions(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retorna histórico cronológico descendente de transações de tokens."""
    use_case = ListTokenTransactionsUseCase(
        ledger_repo=SqlAlchemyTokenLedgerRepository(db),
    )
    transactions = use_case.execute(user_id=current_user.id, limit=limit)
    return [
        {
            "id": str(tx.id),
            "transaction_type": tx.transaction_type,
            "amount": tx.amount,
            "reference_id": tx.reference_id,
            "created_at": tx.created_at.isoformat(),
        }
        for tx in transactions
    ]
