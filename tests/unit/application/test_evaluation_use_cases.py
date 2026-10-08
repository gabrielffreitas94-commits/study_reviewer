"""Testes unitários para casos de uso de avaliação de respostas e gestão de tokens."""

import asyncio
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

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
from src.domain.entities import (
    AnswerEvaluationResult,
    KnowledgeChunk,
    Question,
    Subject,
    TokenLedger,
    TokenTransaction,
    Topic,
    UserQuestionProgress,
)
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    EvaluationServiceError,
    InsufficientTokensError,
    QuestionNotDueError,
    QuestionNotFoundError,
    ResourceOwnershipError,
)


class MockClock:
    def __init__(self, today_date: date | None = None, now_dt: datetime | None = None) -> None:
        self._today = today_date or date(2026, 10, 8)
        self._now = now_dt or datetime(2026, 10, 8, 12, 0, 0, tzinfo=UTC)

    def today(self) -> date:
        return self._today

    def now(self) -> datetime:
        return self._now


def create_mock_repos() -> tuple[Any, ...]:
    q_repo = MagicMock()
    t_repo = MagicMock()
    s_repo = MagicMock()
    p_repo = MagicMock()
    k_repo = MagicMock()
    l_repo = MagicMock()
    eval_svc = MagicMock()
    audit_repo = MagicMock()
    uow = MagicMock()
    clock = MockClock()

    return (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    )


def test_evaluate_student_answer_empty_or_too_long() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo, uow
    )

    user_id = uuid4()
    q_id = uuid4()

    with pytest.raises(DomainValidationError, match="Resposta do estudante não pode ser vazia."):
        asyncio.run(
            use_case.execute(
                EvaluateAnswerInputDTO(question_id=q_id, student_answer="   "),
                user_id=user_id,
            )
        )

    with pytest.raises(
        DomainValidationError, match="Resposta do estudante excede o limite de 10.000 caracteres."
    ):
        asyncio.run(
            use_case.execute(
                EvaluateAnswerInputDTO(question_id=q_id, student_answer="a" * 10001),
                user_id=user_id,
            )
        )


def test_evaluate_student_answer_question_not_found() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    q_repo.get_by_id.return_value = None

    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo, uow
    )

    with pytest.raises(QuestionNotFoundError, match="Pergunta não encontrada."):
        asyncio.run(
            use_case.execute(
                EvaluateAnswerInputDTO(question_id=uuid4(), student_answer="Resposta válida"),
                user_id=uuid4(),
            )
        )


def test_evaluate_student_answer_topic_not_found() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    q_id = uuid4()
    t_id = uuid4()
    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta?", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = None

    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo, uow
    )

    with pytest.raises(EntityNotFoundError, match="Tema não encontrado."):
        asyncio.run(
            use_case.execute(
                EvaluateAnswerInputDTO(question_id=q_id, student_answer="Resposta válida"),
                user_id=uuid4(),
            )
        )


def test_evaluate_student_answer_subject_unauthorized() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    other_user = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta?", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    subject = Subject(id=s_id, owner_id=other_user, name="Matéria Privada", is_public=False)
    s_repo.get_by_id.return_value = subject

    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo, uow
    )

    with pytest.raises(ResourceOwnershipError, match="Acesso negado"):
        asyncio.run(
            use_case.execute(
                EvaluateAnswerInputDTO(question_id=q_id, student_answer="Resposta válida"),
                user_id=user_id,
            )
        )


def test_evaluate_student_answer_question_not_due() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta?", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    subject = Subject(id=s_id, owner_id=user_id, name="Minha Matéria", is_public=False)
    s_repo.get_by_id.return_value = subject

    future_progress = UserQuestionProgress(
        user_id=user_id,
        question_id=q_id,
        current_level=2,
        next_review_date=date(2026, 10, 15),  # no futuro
    )
    p_repo.get_by_user_and_question.return_value = future_progress

    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo, uow
    )

    with pytest.raises(QuestionNotDueError, match="não está vencida para revisão"):
        asyncio.run(
            use_case.execute(
                EvaluateAnswerInputDTO(question_id=q_id, student_answer="Resposta válida"),
                user_id=user_id,
            )
        )


def test_evaluate_student_answer_insufficient_tokens() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta?", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    subject = Subject(id=s_id, owner_id=user_id, name="Minha Matéria", is_public=False)
    s_repo.get_by_id.return_value = subject
    p_repo.get_by_user_and_question.return_value = None

    # Ledger com saldo insuficiente (apenas 100 tokens, exige 500)
    low_ledger = TokenLedger(user_id=user_id, balance=100)
    l_repo.get_by_user_id.return_value = low_ledger

    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo, uow
    )

    with pytest.raises(InsufficientTokensError, match="Saldo insuficiente de tokens"):
        asyncio.run(
            use_case.execute(
                EvaluateAnswerInputDTO(question_id=q_id, student_answer="Resposta válida"),
                user_id=user_id,
            )
        )


def test_evaluate_student_answer_success_with_topic_chunks() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta?", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    subject = Subject(id=s_id, owner_id=user_id, name="Minha Matéria", is_public=False)
    s_repo.get_by_id.return_value = subject
    p_repo.get_by_user_and_question.return_value = None

    # Ledger com 1000 tokens
    ledger = TokenLedger(user_id=user_id, balance=1000)
    l_repo.get_by_user_id.return_value = ledger

    # Chunks no tema
    chunk = KnowledgeChunk(
        source_id=uuid4(),
        topic_id=t_id,
        chunk_index=0,
        content="Evidência do livro sobre o tema.",
        embedding=(0.1, 0.2),
    )
    k_repo.list_by_topic.return_value = [chunk]

    # AI evaluation result
    eval_svc.evaluate_answer = AsyncMock(
        return_value=AnswerEvaluationResult(
            score=100,
            feedback="Muito bom.",
            coverage_score=95,
            accuracy_score=90,
            depth_score=85,
            evidence_quotes=("Citação 1",),
            tokens_used=230,
            cached_context=True,
            evaluation_mode="AI_TEXT",
        )
    )

    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo, uow
    )

    response = asyncio.run(
        use_case.execute(
            EvaluateAnswerInputDTO(question_id=q_id, student_answer="Minha resposta dissertativa"),
            user_id=user_id,
        )
    )

    assert response.score == 100
    assert response.tokens_deducted == 230
    assert response.remaining_token_balance == 770
    assert response.level_before == 0
    assert response.level_after == 1  # promovido para nível 1
    assert response.evidence_quotes == ["Citação 1"]
    assert response.evaluation_mode == "AI_TEXT"

    # Verifica chamadas e auditoria
    p_repo.save.assert_called_once()
    audit_repo.save.assert_called_once()
    assert uow.commit.call_count >= 2


def test_evaluate_student_answer_success_cold_start_fallback() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta?", expected_answer="Gabarito Oficial"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    subject = Subject(id=s_id, owner_id=user_id, name="Minha Matéria", is_public=False)
    s_repo.get_by_id.return_value = subject
    p_repo.get_by_user_and_question.return_value = None

    # Usuário novo sem ledger prévio (testa JIT provisioning de 1000 tokens)
    l_repo.get_by_user_id.return_value = None

    # Sem chunks no tema (Cold-Start)
    k_repo.list_by_topic.return_value = []

    eval_svc.evaluate_answer = AsyncMock(
        return_value=AnswerEvaluationResult(
            score=75,
            feedback="Correto.",
            tokens_used=180,
        )
    )

    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo=None, uow=None
    )

    response = asyncio.run(
        use_case.execute(
            EvaluateAnswerInputDTO(question_id=q_id, student_answer="Minha resposta dissertativa"),
            user_id=user_id,
        )
    )

    assert response.score == 75
    assert response.tokens_deducted == 180
    assert response.remaining_token_balance == 820


def test_evaluate_student_answer_ai_failure_refunds_hold() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta?", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    subject = Subject(id=s_id, owner_id=user_id, name="Minha Matéria", is_public=False)
    s_repo.get_by_id.return_value = subject
    p_repo.get_by_user_and_question.return_value = None

    ledger = TokenLedger(user_id=user_id, balance=1000)
    l_repo.get_by_user_id.return_value = ledger
    k_repo.list_by_topic.return_value = []

    # Provedor de IA falha
    eval_svc.evaluate_answer = AsyncMock(side_effect=RuntimeError("Gemini timeout 503"))

    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo, uow
    )

    with pytest.raises(EvaluationServiceError, match="Falha na inferência"):
        asyncio.run(
            use_case.execute(
                EvaluateAnswerInputDTO(
                    question_id=q_id, student_answer="Minha resposta dissertativa"
                ),
                user_id=user_id,
            )
        )

    # Verifica que o hold foi estornado: held_balance voltou a 0 e balance permaneceu 1000
    assert ledger.held_balance == 0
    assert ledger.balance == 1000
    assert ledger.available_balance == 1000


def test_evaluate_student_answer_domain_exception_refunds_hold() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        eval_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta?", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    subject = Subject(id=s_id, owner_id=user_id, name="Minha Matéria", is_public=False)
    s_repo.get_by_id.return_value = subject
    p_repo.get_by_user_and_question.return_value = None

    ledger = TokenLedger(user_id=user_id, balance=1000)
    l_repo.get_by_user_id.return_value = ledger
    k_repo.list_by_topic.return_value = []

    eval_svc.evaluate_answer = AsyncMock(side_effect=DomainValidationError("Erro de domínio"))

    use_case = EvaluateStudentAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, eval_svc, clock, audit_repo, uow
    )

    with pytest.raises(DomainValidationError, match="Erro de domínio"):
        asyncio.run(
            use_case.execute(
                EvaluateAnswerInputDTO(
                    question_id=q_id, student_answer="Minha resposta dissertativa"
                ),
                user_id=user_id,
            )
        )

    assert ledger.held_balance == 0
    assert ledger.balance == 1000


def test_get_user_token_balance_existing_and_new() -> None:
    l_repo = MagicMock()
    use_case = GetUserTokenBalanceUseCase(l_repo)

    # Novo usuário (JIT 1000 tokens)
    user_id_1 = uuid4()
    l_repo.get_by_user_id.return_value = None
    balance_1 = use_case.execute(user_id_1)
    assert balance_1.balance == 1000
    assert balance_1.available_balance == 1000
    l_repo.save.assert_called_once()

    # Usuário existente
    user_id_2 = uuid4()
    l_repo.get_by_user_id.return_value = TokenLedger(
        user_id=user_id_2, balance=2500, held_balance=500
    )
    balance_2 = use_case.execute(user_id_2)
    assert balance_2.balance == 2500
    assert balance_2.held_balance == 500
    assert balance_2.available_balance == 2000


def test_deposit_tokens_use_case() -> None:
    l_repo = MagicMock()
    uow = MagicMock()
    use_case = DepositTokensUseCase(l_repo, uow)

    user_id = uuid4()

    # Depósito inválido
    with pytest.raises(DomainValidationError, match="A quantidade de depósito deve ser positiva."):
        use_case.execute(DepositTokensInputDTO(amount=0), user_id)

    # Depósito com usuário novo
    l_repo.get_by_user_id.return_value = None
    res = use_case.execute(DepositTokensInputDTO(amount=1000), user_id)
    assert res.balance == 1000
    l_repo.save.assert_called_once()
    l_repo.record_transaction.assert_called_once()
    uow.commit.assert_called_once()


def test_list_token_transactions_use_case() -> None:
    l_repo = MagicMock()
    use_case = ListTokenTransactionsUseCase(l_repo)

    user_id = uuid4()
    now = datetime.now(UTC)
    tx = TokenTransaction(
        user_id=user_id,
        transaction_type="DEPOSIT",
        amount=500,
        reference_id="TEST",
        created_at=now,
    )
    l_repo.list_transactions.return_value = [tx]

    transactions = use_case.execute(user_id=user_id, limit=10)
    assert len(transactions) == 1
    assert transactions[0].transaction_type == "DEPOSIT"
    assert transactions[0].amount == 500
    assert transactions[0].reference_id == "TEST"
    assert transactions[0].created_at == now
