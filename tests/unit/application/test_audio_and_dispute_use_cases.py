"""Testes unitários para casos de uso de avaliação em áudio e conselho multiagente (Sprint 09)."""

import asyncio
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.dto.evaluation_dto import (
    DisputeEvaluationInputDTO,
    EvaluateAudioAnswerInputDTO,
)
from src.application.use_cases.evaluation_use_cases import (
    DisputeEvaluationUseCase,
    EvaluateAudioAnswerUseCase,
)
from src.domain.entities import (
    AnswerEvaluationResult,
    DisputeEvaluationResult,
    KnowledgeChunk,
    Question,
    Subject,
    TokenLedger,
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
    audio_svc = MagicMock()
    dispute_svc = MagicMock()
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
        audio_svc,
        dispute_svc,
        audit_repo,
        uow,
        clock,
    )


# ============================================================================
# Testes do EvaluateAudioAnswerUseCase
# ============================================================================


def test_evaluate_audio_empty_or_too_large() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    use_case = EvaluateAudioAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, audio_svc, clock, audit_repo, uow
    )

    user_id = uuid4()
    q_id = uuid4()

    with pytest.raises(DomainValidationError, match="Arquivo de áudio não pode ser vazio."):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=q_id, audio_bytes=b"", mime_type="audio/webm"
                ),
                user_id=user_id,
            )
        )

    with pytest.raises(
        DomainValidationError,
        match="Tamanho do arquivo de áudio excede o limite máximo permitido de 10MB.",
    ):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=q_id,
                    audio_bytes=b"0" * (10 * 1024 * 1024 + 1),
                    mime_type="audio/webm",
                ),
                user_id=user_id,
            )
        )


def test_evaluate_audio_invalid_mime_type() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    use_case = EvaluateAudioAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, audio_svc, clock, audit_repo, uow
    )

    user_id = uuid4()
    q_id = uuid4()

    with pytest.raises(DomainValidationError, match="Formato de áudio não suportado"):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=q_id, audio_bytes=b"fake-bytes", mime_type="video/mp4"
                ),
                user_id=user_id,
            )
        )


def test_evaluate_audio_question_not_found() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    q_repo.get_by_id.return_value = None

    use_case = EvaluateAudioAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, audio_svc, clock, audit_repo, uow
    )

    with pytest.raises(QuestionNotFoundError, match="Pergunta não encontrada."):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=uuid4(), audio_bytes=b"fake-bytes", mime_type="audio/webm"
                ),
                user_id=uuid4(),
            )
        )


def test_evaluate_audio_topic_and_subject_errors() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Q", expected_answer="A"
    )
    t_repo.get_by_id.return_value = None

    use_case = EvaluateAudioAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, audio_svc, clock, audit_repo, uow
    )

    with pytest.raises(EntityNotFoundError, match="Tema não encontrado."):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=q_id, audio_bytes=b"fake-bytes", mime_type="audio/webm"
                ),
                user_id=user_id,
            )
        )

    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Materia", owner_id=uuid4())

    with pytest.raises(ResourceOwnershipError, match="Acesso negado para estudar esta pergunta."):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=q_id, audio_bytes=b"fake-bytes", mime_type="audio/webm"
                ),
                user_id=user_id,
            )
        )


def test_evaluate_audio_question_not_due() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Q", expected_answer="A"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Materia", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = UserQuestionProgress(
        user_id=user_id,
        question_id=q_id,
        current_level=2,
        next_review_date=date(2026, 10, 15),
    )

    use_case = EvaluateAudioAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, audio_svc, clock, audit_repo, uow
    )

    with pytest.raises(QuestionNotDueError, match="não está vencida para revisão"):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=q_id, audio_bytes=b"fake-bytes", mime_type="audio/webm"
                ),
                user_id=user_id,
            )
        )


def test_evaluate_audio_insufficient_tokens() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Q", expected_answer="A"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Materia", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = None
    l_repo.get_by_user_id.return_value = TokenLedger(user_id=user_id, balance=100)

    use_case = EvaluateAudioAnswerUseCase(
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        clock,
        audit_repo,
        uow,
        estimated_hold_tokens=800,
    )

    with pytest.raises(InsufficientTokensError, match="Saldo insuficiente de tokens"):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=q_id, audio_bytes=b"fake-bytes", mime_type="audio/webm"
                ),
                user_id=user_id,
            )
        )


def test_evaluate_audio_success_and_cold_start() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta", expected_answer="Gabarito Canônico"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Matéria", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = None
    k_repo.list_by_topic.return_value = []
    l_repo.get_by_user_id.return_value = TokenLedger(user_id=user_id, balance=2000)

    audio_svc.evaluate_audio_answer = AsyncMock(
        return_value=AnswerEvaluationResult(
            score=100,
            feedback="Excelente fala.",
            coverage_score=100,
            accuracy_score=100,
            depth_score=100,
            tokens_used=250,
            evaluation_mode="AI_AUDIO",
            transcribed_text="Gabarito Canônico falado perfeitamente.",
        )
    )

    use_case = EvaluateAudioAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, audio_svc, clock, audit_repo, uow
    )

    response = asyncio.run(
        use_case.execute(
            EvaluateAudioAnswerInputDTO(
                question_id=q_id,
                audio_bytes=b"fake-audio-bytes",
                mime_type="audio/webm",
            ),
            user_id=user_id,
        )
    )

    assert response.score == 100
    assert response.evaluation_mode == "AI_AUDIO"
    assert response.transcribed_text == "Gabarito Canônico falado perfeitamente."
    assert response.level_after == 1  # Promoted from 0 to 1 on score 100
    assert response.tokens_deducted == 250
    assert audit_repo.save.called
    assert uow.commit.called


def test_evaluate_audio_service_error_refunds_hold() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Matéria", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = None
    k_repo.list_by_topic.return_value = [
        KnowledgeChunk(
            id=uuid4(),
            source_id=uuid4(),
            topic_id=t_id,
            chunk_index=0,
            content="Contexto relevante",
            embedding=tuple([0.1] * 768),
        )
    ]
    ledger = TokenLedger(user_id=user_id, balance=2000)
    l_repo.get_by_user_id.return_value = ledger

    audio_svc.evaluate_audio_answer = AsyncMock(
        side_effect=RuntimeError("Timeout no Gemini multimodal")
    )

    use_case = EvaluateAudioAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, audio_svc, clock, audit_repo, uow
    )

    with pytest.raises(
        EvaluationServiceError, match="Falha na inferência de áudio do modelo de IA"
    ):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=q_id,
                    audio_bytes=b"fake-audio-bytes",
                    mime_type="audio/webm",
                ),
                user_id=user_id,
            )
        )

    # Verifica que o hold foi cancelado e o saldo retido voltou a zero
    assert ledger.held_balance == 0
    assert ledger.available_balance == 2000


# ============================================================================
# Testes do DisputeEvaluationUseCase
# ============================================================================


def test_dispute_validation_errors() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        _,
        dispute_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    use_case = DisputeEvaluationUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, dispute_svc, clock, audit_repo, uow
    )

    user_id = uuid4()
    q_id = uuid4()

    with pytest.raises(DomainValidationError, match="Resposta do estudante não pode ser vazia."):
        asyncio.run(
            use_case.execute(
                DisputeEvaluationInputDTO(
                    question_id=q_id,
                    student_answer="  ",
                    dispute_argument="Argumento válido suficiente.",
                ),
                user_id=user_id,
            )
        )

    with pytest.raises(
        DomainValidationError,
        match="Argumento de contestação deve conter entre 5 e 5.000 caracteres.",
    ):
        asyncio.run(
            use_case.execute(
                DisputeEvaluationInputDTO(
                    question_id=q_id,
                    student_answer="Minha resposta",
                    dispute_argument="Oi",
                ),
                user_id=user_id,
            )
        )


def test_dispute_question_and_ownership_errors() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        _,
        dispute_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = None
    use_case = DisputeEvaluationUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, dispute_svc, clock, audit_repo, uow
    )

    with pytest.raises(QuestionNotFoundError, match="Pergunta não encontrada."):
        asyncio.run(
            use_case.execute(
                DisputeEvaluationInputDTO(
                    question_id=q_id,
                    student_answer="Minha resposta",
                    dispute_argument="Argumento fundamentado válido.",
                ),
                user_id=user_id,
            )
        )

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Q", expected_answer="A"
    )
    t_repo.get_by_id.return_value = None

    with pytest.raises(EntityNotFoundError, match="Tema não encontrado."):
        asyncio.run(
            use_case.execute(
                DisputeEvaluationInputDTO(
                    question_id=q_id,
                    student_answer="Minha resposta",
                    dispute_argument="Argumento fundamentado válido.",
                ),
                user_id=user_id,
            )
        )

    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Materia", owner_id=uuid4())

    with pytest.raises(ResourceOwnershipError, match="Acesso negado para contestar esta pergunta."):
        asyncio.run(
            use_case.execute(
                DisputeEvaluationInputDTO(
                    question_id=q_id,
                    student_answer="Minha resposta",
                    dispute_argument="Argumento fundamentado válido.",
                ),
                user_id=user_id,
            )
        )


def test_dispute_insufficient_tokens() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        _,
        dispute_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Q", expected_answer="A"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Materia", owner_id=user_id)
    l_repo.get_by_user_id.return_value = TokenLedger(user_id=user_id, balance=300)

    use_case = DisputeEvaluationUseCase(
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        dispute_svc,
        clock,
        audit_repo,
        uow,
        estimated_hold_tokens=1000,
    )

    with pytest.raises(InsufficientTokensError, match="Saldo insuficiente de tokens"):
        asyncio.run(
            use_case.execute(
                DisputeEvaluationInputDTO(
                    question_id=q_id,
                    student_answer="Minha resposta",
                    dispute_argument="Argumento fundamentado com doutrina.",
                ),
                user_id=user_id,
            )
        )


def test_dispute_upheld_success_promotes_srs_and_refunds_tokens() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        _,
        dispute_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Matéria", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = UserQuestionProgress(
        user_id=user_id,
        question_id=q_id,
        current_level=1,
        next_review_date=date(2026, 10, 8),
    )
    k_repo.list_by_topic.return_value = []
    ledger = TokenLedger(user_id=user_id, balance=3000)
    l_repo.get_by_user_id.return_value = ledger

    dispute_svc.dispute_evaluation = AsyncMock(
        return_value=DisputeEvaluationResult(
            status="UPHELD",
            revised_score=100,
            advocate_rationale="Advogado constatou pertinência dos argumentos.",
            critic_rationale="Crítico validou a conformidade factual.",
            arbitrator_verdict="Veredito: procedente com nota 100.",
            tokens_used=450,
            refund_dispute_tokens=True,
        )
    )

    use_case = DisputeEvaluationUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, dispute_svc, clock, audit_repo, uow
    )

    response = asyncio.run(
        use_case.execute(
            DisputeEvaluationInputDTO(
                question_id=q_id,
                student_answer="Minha resposta original",
                dispute_argument="Argumento fundamentado de contestação.",
            ),
            user_id=user_id,
        )
    )

    assert response.status == "UPHELD"
    assert response.revised_score == 100
    assert response.refund_dispute_tokens is True
    assert response.tokens_deducted == 0
    assert response.level_after == 2  # Promovido de nível 1 para nível 2 com nota 100!
    assert ledger.held_balance == 0
    assert ledger.available_balance == 3000
    assert audit_repo.save.called
    assert uow.commit.called


def test_dispute_rejected_settles_tokens_and_keeps_level() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        _,
        dispute_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Matéria", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = UserQuestionProgress(
        user_id=user_id,
        question_id=q_id,
        current_level=1,
        next_review_date=date(2026, 10, 8),
    )
    ledger = TokenLedger(user_id=user_id, balance=3000)
    l_repo.get_by_user_id.return_value = ledger

    dispute_svc.dispute_evaluation = AsyncMock(
        return_value=DisputeEvaluationResult(
            status="REJECTED",
            revised_score=30,
            advocate_rationale="Argumento frágil.",
            critic_rationale="Não procede.",
            arbitrator_verdict="Veredito: improcedente. Nota mantida.",
            tokens_used=400,
            refund_dispute_tokens=False,
        )
    )

    use_case = DisputeEvaluationUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, dispute_svc, clock, audit_repo, uow
    )

    response = asyncio.run(
        use_case.execute(
            DisputeEvaluationInputDTO(
                question_id=q_id,
                student_answer="Minha resposta original",
                dispute_argument="Argumento de contestação que foi rejeitado.",
            ),
            user_id=user_id,
        )
    )

    assert response.status == "REJECTED"
    assert response.revised_score == 30
    assert response.refund_dispute_tokens is False
    assert response.tokens_deducted == 400
    assert response.level_after == 1  # Mantido nível 1
    assert ledger.held_balance == 0
    assert ledger.available_balance == 2600


def test_dispute_service_error_refunds_hold() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        _,
        dispute_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Matéria", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = None
    ledger = TokenLedger(user_id=user_id, balance=3000)
    l_repo.get_by_user_id.return_value = ledger

    dispute_svc.dispute_evaluation = AsyncMock(
        side_effect=RuntimeError("Instabilidade temporária na câmara multiagente")
    )

    use_case = DisputeEvaluationUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, dispute_svc, clock, audit_repo, uow
    )

    with pytest.raises(
        EvaluationServiceError, match="Falha na deliberação da câmara multiagente de IA"
    ):
        asyncio.run(
            use_case.execute(
                DisputeEvaluationInputDTO(
                    question_id=q_id,
                    student_answer="Minha resposta original",
                    dispute_argument="Argumento de contestação válido.",
                ),
                user_id=user_id,
            )
        )

    assert ledger.held_balance == 0
    assert ledger.available_balance == 3000


def test_evaluate_audio_ledger_none_initializes_default() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Matéria", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = None
    l_repo.get_by_user_id.return_value = None  # Testa linhas 416-418
    k_repo.list_by_topic.return_value = []

    audio_svc.evaluate_audio_answer = AsyncMock(
        return_value=AnswerEvaluationResult(
            score=90,
            feedback="Bom.",
            coverage_score=90,
            accuracy_score=90,
            depth_score=90,
            tokens_used=200,
            evaluation_mode="AI_AUDIO",
            transcribed_text="Texto",
        )
    )

    use_case = EvaluateAudioAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, audio_svc, clock, audit_repo, uow
    )

    res = asyncio.run(
        use_case.execute(
            EvaluateAudioAnswerInputDTO(
                question_id=q_id, audio_bytes=b"bytes", mime_type="audio/webm"
            ),
            user_id=user_id,
        )
    )
    assert res.score == 90
    assert l_repo.save.called


def test_evaluate_audio_service_raises_domain_exception() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        audio_svc,
        _,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Matéria", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = None
    ledger = TokenLedger(user_id=user_id, balance=2000)
    l_repo.get_by_user_id.return_value = ledger

    # Testa linha 464 (re-raise de DomainException)
    audio_svc.evaluate_audio_answer = AsyncMock(
        side_effect=DomainValidationError("Falha de validação no adaptador")
    )

    use_case = EvaluateAudioAnswerUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, audio_svc, clock, audit_repo, uow
    )

    with pytest.raises(DomainValidationError, match="Falha de validação no adaptador"):
        asyncio.run(
            use_case.execute(
                EvaluateAudioAnswerInputDTO(
                    question_id=q_id, audio_bytes=b"bytes", mime_type="audio/webm"
                ),
                user_id=user_id,
            )
        )
    assert ledger.held_balance == 0


def test_dispute_ledger_none_initializes_default() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        _,
        dispute_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Matéria", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = None
    l_repo.get_by_user_id.return_value = None  # Testa linhas 614-615

    dispute_svc.dispute_evaluation = AsyncMock(
        return_value=DisputeEvaluationResult(
            status="REJECTED",
            revised_score=20,
            advocate_rationale="Adv.",
            critic_rationale="Crit.",
            arbitrator_verdict="Veredito.",
            tokens_used=300,
            refund_dispute_tokens=False,
        )
    )

    use_case = DisputeEvaluationUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, dispute_svc, clock, audit_repo, uow
    )

    res = asyncio.run(
        use_case.execute(
            DisputeEvaluationInputDTO(
                question_id=q_id,
                student_answer="Resposta",
                dispute_argument="Argumento de contestação válido.",
            ),
            user_id=user_id,
        )
    )
    assert res.status == "REJECTED"
    assert l_repo.save.called


def test_dispute_service_raises_domain_exception() -> None:
    (
        q_repo,
        t_repo,
        s_repo,
        p_repo,
        k_repo,
        l_repo,
        _,
        dispute_svc,
        audit_repo,
        uow,
        clock,
    ) = create_mock_repos()
    user_id = uuid4()
    q_id = uuid4()
    t_id = uuid4()
    s_id = uuid4()

    q_repo.get_by_id.return_value = Question(
        id=q_id, topic_id=t_id, prompt="Pergunta", expected_answer="Gabarito"
    )
    t_repo.get_by_id.return_value = Topic(id=t_id, subject_id=s_id, name="Tema")
    s_repo.get_by_id.return_value = Subject(id=s_id, name="Matéria", owner_id=user_id)
    p_repo.get_by_user_and_question.return_value = None
    ledger = TokenLedger(user_id=user_id, balance=3000)
    l_repo.get_by_user_id.return_value = ledger

    # Testa linha 663 (re-raise de DomainException)
    dispute_svc.dispute_evaluation = AsyncMock(
        side_effect=DomainValidationError("Falha de domínio na câmara")
    )

    use_case = DisputeEvaluationUseCase(
        q_repo, t_repo, s_repo, p_repo, k_repo, l_repo, dispute_svc, clock, audit_repo, uow
    )

    with pytest.raises(DomainValidationError, match="Falha de domínio na câmara"):
        asyncio.run(
            use_case.execute(
                DisputeEvaluationInputDTO(
                    question_id=q_id,
                    student_answer="Resposta",
                    dispute_argument="Argumento de contestação válido.",
                ),
                user_id=user_id,
            )
        )
    assert ledger.held_balance == 0
