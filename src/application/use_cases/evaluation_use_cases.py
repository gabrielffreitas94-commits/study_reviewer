"""Casos de uso para avaliação semântica aterrada de respostas e tarifação de tokens."""

import logging
from typing import Any
from uuid import UUID

from src.application.dto.evaluation_dto import (
    DepositTokensInputDTO,
    EvaluateAnswerInputDTO,
    EvaluateAnswerResponseDTO,
    TokenTransactionDTO,
    UserTokenBalanceDTO,
)
from src.application.ports.repositories import (
    IKnowledgeChunkRepository,
    IQuestionProgressRepository,
    IQuestionRepository,
    IReviewAuditRepository,
    ISubjectRepository,
    ITokenLedgerRepository,
    ITopicRepository,
)
from src.domain.entities import (
    ReviewAuditLog,
    TokenLedger,
    TokenTransaction,
    UserQuestionProgress,
)
from src.domain.exceptions import (
    DomainException,
    DomainValidationError,
    EntityNotFoundError,
    EvaluationServiceError,
    QuestionNotDueError,
    QuestionNotFoundError,
    ResourceOwnershipError,
)
from src.domain.protocols import IAnswerEvaluationService
from src.domain.services import SpacingPolicyService

logger = logging.getLogger(__name__)


class EvaluateStudentAnswerUseCase:
    """Orquestra a avaliação semântica aterrada com retenção preventiva e liquidação de tokens."""

    def __init__(
        self,
        question_repo: IQuestionRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
        progress_repo: IQuestionProgressRepository,
        chunk_repo: IKnowledgeChunkRepository,
        ledger_repo: ITokenLedgerRepository,
        evaluation_service: IAnswerEvaluationService,
        clock: Any,
        audit_repo: IReviewAuditRepository | None = None,
        uow: Any | None = None,
        estimated_hold_tokens: int = 500,
    ) -> None:
        self._question_repo = question_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo
        self._progress_repo = progress_repo
        self._chunk_repo = chunk_repo
        self._ledger_repo = ledger_repo
        self._evaluation_service = evaluation_service
        self._clock = clock
        self._audit_repo = audit_repo
        self._uow = uow
        self._estimated_hold_tokens = estimated_hold_tokens

    async def execute(
        self, dto: EvaluateAnswerInputDTO, user_id: UUID
    ) -> EvaluateAnswerResponseDTO:
        # 1. Validação da resposta
        clean_answer = dto.student_answer.strip() if dto.student_answer else ""
        if not clean_answer:
            raise DomainValidationError("Resposta do estudante não pode ser vazia.")
        if len(clean_answer) > 10_000:
            raise DomainValidationError(
                "Resposta do estudante excede o limite de 10.000 caracteres."
            )

        # 2. Pergunta, tema e matéria
        question = self._question_repo.get_by_id(dto.question_id)
        if not question:
            raise QuestionNotFoundError("Pergunta não encontrada.")

        topic = self._topic_repo.get_by_id(question.topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_studied_by(user_id):
            raise ResourceOwnershipError("Acesso negado para estudar esta pergunta.")

        # 3. Verificação de repetição espaçada (SRS)
        today = self._clock.today()
        progress = self._progress_repo.get_by_user_and_question(user_id, dto.question_id)
        if progress is None:
            progress = UserQuestionProgress(
                user_id=user_id,
                question_id=dto.question_id,
                current_level=0,
                next_review_date=today,
            )

        if progress.next_review_date > today:
            raise QuestionNotDueError(
                f"A pergunta '{dto.question_id}' não está vencida para revisão "
                f"(vencimento: {progress.next_review_date})."
            )

        # 4. Retenção preventiva de tokens (Pre-Auth Hold)
        ledger = self._ledger_repo.get_by_user_id(user_id)
        if ledger is None:
            ledger = TokenLedger(user_id=user_id, balance=1000)
            self._ledger_repo.save(ledger)

        hold_amount = self._estimated_hold_tokens
        ledger.hold(hold_amount)
        self._ledger_repo.save(ledger)

        hold_tx = TokenTransaction(
            user_id=user_id,
            transaction_type="HOLD",
            amount=hold_amount,
            reference_id=str(dto.question_id),
        )
        self._ledger_repo.record_transaction(hold_tx)
        if self._uow is not None:
            self._uow.commit()

        # 5. Recuperação de contexto RAG com fallback para Cold-Start
        chunks = self._chunk_repo.list_by_topic(topic.id)
        if chunks:
            context_chunks = [c.content for c in chunks[:5]]
        else:
            context_chunks = [f"Gabarito Canônico Oficial: {question.expected_answer}"]

        # 6. Avaliação semântica via IA com estorno em caso de falha
        try:
            eval_result = await self._evaluation_service.evaluate_answer(
                prompt=question.prompt,
                expected_answer=question.expected_answer,
                student_answer=clean_answer,
                context_chunks=context_chunks,
            )
        except Exception as exc:
            # Estorno defensivo integral do hold
            ledger.refund_hold(hold_amount)
            self._ledger_repo.save(ledger)
            refund_tx = TokenTransaction(
                user_id=user_id,
                transaction_type="REFUND",
                amount=hold_amount,
                reference_id=str(dto.question_id),
            )
            self._ledger_repo.record_transaction(refund_tx)
            if self._uow is not None:
                self._uow.commit()

            if isinstance(exc, DomainException):
                raise
            raise EvaluationServiceError(f"Falha na inferência do modelo de IA: {exc}") from exc

        # 7. Liquidação definitiva de tokens (Settlement)
        actual_tokens = eval_result.tokens_used if eval_result.tokens_used > 0 else 120
        ledger.settle(hold_amount=hold_amount, actual_tokens=actual_tokens)
        self._ledger_repo.save(ledger)

        settle_tx = TokenTransaction(
            user_id=user_id,
            transaction_type="SETTLEMENT",
            amount=actual_tokens,
            reference_id=str(dto.question_id),
        )
        self._ledger_repo.record_transaction(settle_tx)

        # 8. Atualização do SRS e Auditoria
        previous_level = progress.current_level
        new_level, next_date = SpacingPolicyService.calculate_next_schedule(
            current_level=previous_level,
            score=eval_result.score,
            review_date=today,
        )

        now = self._clock.now()
        progress.apply_review(
            new_level=new_level,
            next_date=next_date,
            reviewed_at=now,
        )
        self._progress_repo.save(progress)

        if self._audit_repo is not None:
            audit_log = ReviewAuditLog(
                user_id=user_id,
                question_id=dto.question_id,
                subject_id=subject.id,
                topic_id=topic.id,
                historical_subject_name=subject.name,
                historical_topic_name=topic.name,
                review_date=today,
                score=eval_result.score,
                level_before=previous_level,
                level_after=new_level,
                evaluation_mode="AI_TEXT",
                logged_at=now,
            )
            self._audit_repo.save(audit_log)

        if self._uow is not None:
            self._uow.commit()

        logger.info(
            "ai_text_evaluation_completed: user=%s question=%s score=%s tokens=%s",
            user_id,
            dto.question_id,
            eval_result.score,
            actual_tokens,
        )

        return EvaluateAnswerResponseDTO(
            question_id=dto.question_id,
            score=eval_result.score,
            feedback=eval_result.feedback,
            coverage_score=eval_result.coverage_score,
            accuracy_score=eval_result.accuracy_score,
            depth_score=eval_result.depth_score,
            evidence_quotes=list(eval_result.evidence_quotes),
            level_before=previous_level,
            level_after=new_level,
            next_review_date=next_date,
            tokens_deducted=actual_tokens,
            remaining_token_balance=ledger.available_balance,
            evaluation_mode="AI_TEXT",
        )


class GetUserTokenBalanceUseCase:
    """Recupera o extrato/saldo atual de tokens do usuário com provisionamento JIT."""

    def __init__(self, ledger_repo: ITokenLedgerRepository) -> None:
        self._ledger_repo = ledger_repo

    def execute(self, user_id: UUID) -> UserTokenBalanceDTO:
        ledger = self._ledger_repo.get_by_user_id(user_id)
        if ledger is None:
            ledger = TokenLedger(user_id=user_id, balance=1000)
            self._ledger_repo.save(ledger)

        return UserTokenBalanceDTO(
            user_id=user_id,
            balance=ledger.balance,
            held_balance=ledger.held_balance,
            available_balance=ledger.available_balance,
        )


class DepositTokensUseCase:
    """Credita tokens no ledger do estudante (compra ou concessão administrativa)."""

    def __init__(
        self,
        ledger_repo: ITokenLedgerRepository,
        uow: Any | None = None,
    ) -> None:
        self._ledger_repo = ledger_repo
        self._uow = uow

    def execute(self, dto: DepositTokensInputDTO, user_id: UUID) -> UserTokenBalanceDTO:
        if dto.amount <= 0:
            raise DomainValidationError("A quantidade de depósito deve ser positiva.")

        ledger = self._ledger_repo.get_by_user_id(user_id)
        if ledger is None:
            ledger = TokenLedger(user_id=user_id, balance=0)

        ledger.deposit(dto.amount)
        self._ledger_repo.save(ledger)

        tx = TokenTransaction(
            user_id=user_id,
            transaction_type="DEPOSIT",
            amount=dto.amount,
            reference_id="MANUAL_DEPOSIT",
        )
        self._ledger_repo.record_transaction(tx)

        if self._uow is not None:
            self._uow.commit()

        return UserTokenBalanceDTO(
            user_id=user_id,
            balance=ledger.balance,
            held_balance=ledger.held_balance,
            available_balance=ledger.available_balance,
        )


class ListTokenTransactionsUseCase:
    """Lista as transações mais recentes do ledger de tokens do estudante."""

    def __init__(self, ledger_repo: ITokenLedgerRepository) -> None:
        self._ledger_repo = ledger_repo

    def execute(self, user_id: UUID, limit: int = 50) -> list[TokenTransactionDTO]:
        transactions = self._ledger_repo.list_transactions(user_id=user_id, limit=limit)
        return [
            TokenTransactionDTO(
                id=tx.id,
                transaction_type=tx.transaction_type,
                amount=tx.amount,
                reference_id=tx.reference_id,
                created_at=tx.created_at,
            )
            for tx in transactions
        ]
