"""Testes unitários para entidades de áudio e conselho multiagente de contestação (Sprint 09)."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from src.domain.entities import (
    AnswerEvaluationResult,
    DisputeEvaluationResult,
    ReviewAuditLog,
)
from src.domain.exceptions import DomainValidationError


def test_dispute_evaluation_result_valid_upheld() -> None:
    result = DisputeEvaluationResult(
        status="UPHELD",
        revised_score=85,
        advocate_rationale="O aluno abordou a corrente minoritária amparada no chunk 1.",
        critic_rationale="A corrente existe factualmente, embora haja divergência doutrinária.",
        arbitrator_verdict="Contestação aceita. Nota revisada para 85 com respaldo bibliográfico.",
        tokens_used=420,
        refund_dispute_tokens=True,
    )
    assert result.status == "UPHELD"
    assert result.revised_score == 85
    assert result.refund_dispute_tokens is True
    assert result.tokens_used == 420


def test_dispute_evaluation_result_valid_rejected() -> None:
    result = DisputeEvaluationResult(
        status="REJECTED",
        revised_score=30,
        advocate_rationale="O aluno tenta justificar omissão alegando sinônimo inexistente.",
        critic_rationale="A alegação é inconsistente com as fontes canônicas cadastradas.",
        arbitrator_verdict="Contestação rejeitada. Nota original mantida em 30.",
        tokens_used=380,
        refund_dispute_tokens=False,
    )
    assert result.status == "REJECTED"
    assert result.revised_score == 30
    assert result.refund_dispute_tokens is False


def test_dispute_evaluation_result_invalid_status() -> None:
    with pytest.raises(DomainValidationError, match="Status de contestação inválido"):
        DisputeEvaluationResult(
            status="MAYBE",
            revised_score=50,
            advocate_rationale="Parecer favorável",
            critic_rationale="Parecer crítico",
            arbitrator_verdict="Veredito final",
        )


def test_dispute_evaluation_result_invalid_scores() -> None:
    with pytest.raises(DomainValidationError, match="O revised_score deve estar entre 0 e 100"):
        DisputeEvaluationResult(
            status="UPHELD",
            revised_score=-1,
            advocate_rationale="Parecer favorável",
            critic_rationale="Parecer crítico",
            arbitrator_verdict="Veredito final",
        )

    with pytest.raises(DomainValidationError, match="O revised_score deve estar entre 0 e 100"):
        DisputeEvaluationResult(
            status="UPHELD",
            revised_score=101,
            advocate_rationale="Parecer favorável",
            critic_rationale="Parecer crítico",
            arbitrator_verdict="Veredito final",
        )


def test_dispute_evaluation_result_empty_rationales() -> None:
    with pytest.raises(DomainValidationError, match="O parecer do advogado não pode ser vazio"):
        DisputeEvaluationResult(
            status="UPHELD",
            revised_score=80,
            advocate_rationale="   ",
            critic_rationale="Parecer crítico",
            arbitrator_verdict="Veredito final",
        )

    with pytest.raises(DomainValidationError, match="O parecer do crítico não pode ser vazio"):
        DisputeEvaluationResult(
            status="UPHELD",
            revised_score=80,
            advocate_rationale="Parecer favorável",
            critic_rationale="",
            arbitrator_verdict="Veredito final",
        )

    with pytest.raises(DomainValidationError, match="O veredito do árbitro não pode ser vazio"):
        DisputeEvaluationResult(
            status="UPHELD",
            revised_score=80,
            advocate_rationale="Parecer favorável",
            critic_rationale="Parecer crítico",
            arbitrator_verdict=" \n  ",
        )


def test_dispute_evaluation_result_negative_tokens() -> None:
    with pytest.raises(DomainValidationError, match="Tokens consumidos não podem ser negativos"):
        DisputeEvaluationResult(
            status="UPHELD",
            revised_score=80,
            advocate_rationale="Parecer favorável",
            critic_rationale="Parecer crítico",
            arbitrator_verdict="Veredito final",
            tokens_used=-5,
        )


def test_answer_evaluation_result_with_audio_and_transcription() -> None:
    res = AnswerEvaluationResult(
        score=90,
        feedback="Excelente resposta falada.",
        coverage_score=95,
        accuracy_score=90,
        depth_score=85,
        evaluation_mode="AI_AUDIO",
        transcribed_text="O mandado de segurança é cabível para proteger direito líquido e certo.",
    )
    assert res.evaluation_mode == "AI_AUDIO"
    assert res.transcribed_text is not None
    assert "mandado de segurança" in res.transcribed_text


def test_answer_evaluation_result_with_multiagent_dispute_mode() -> None:
    res = AnswerEvaluationResult(
        score=95,
        feedback="Revisão homologada pelo conselho multiagente.",
        evaluation_mode="MULTIAGENT_DISPUTE",
    )
    assert res.evaluation_mode == "MULTIAGENT_DISPUTE"


def test_review_audit_log_with_sprint_09_modes() -> None:
    user_id = uuid4()
    q_id = uuid4()
    s_id = uuid4()
    t_id = uuid4()
    now = datetime.now(UTC)

    audio_log = ReviewAuditLog(
        user_id=user_id,
        question_id=q_id,
        subject_id=s_id,
        topic_id=t_id,
        historical_subject_name="Direito Constitucional",
        historical_topic_name="Remédios Constitucionais",
        review_date=date(2026, 10, 8),
        score=85,
        level_before=1,
        level_after=1,
        evaluation_mode="AI_AUDIO",
        logged_at=now,
    )
    assert audio_log.evaluation_mode == "AI_AUDIO"

    dispute_log = ReviewAuditLog(
        user_id=user_id,
        question_id=q_id,
        subject_id=s_id,
        topic_id=t_id,
        historical_subject_name="Direito Constitucional",
        historical_topic_name="Remédios Constitucionais",
        review_date=date(2026, 10, 8),
        score=100,
        level_before=1,
        level_after=2,
        evaluation_mode="MULTIAGENT_DISPUTE",
        logged_at=now,
    )
    assert dispute_log.evaluation_mode == "MULTIAGENT_DISPUTE"
    assert dispute_log.is_promoted is True
