"""Testes unitários para a entidade ReviewAuditLog (Sprint 04)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from src.domain.entities import ReviewAuditLog
from src.domain.exceptions import DomainValidationError


@pytest.mark.unit
def test_review_audit_log_creation_valid() -> None:
    """Verifica a criação nominal e propriedades de ReviewAuditLog."""
    user_id = uuid4()
    question_id = uuid4()
    subject_id = uuid4()
    topic_id = uuid4()
    now = datetime.now(UTC)
    today = date(2026, 10, 7)

    log = ReviewAuditLog(
        user_id=user_id,
        question_id=question_id,
        subject_id=subject_id,
        topic_id=topic_id,
        historical_subject_name="Direito Constitucional",
        historical_topic_name="Controle de Constitucionalidade",
        review_date=today,
        score=100,
        level_before=2,
        level_after=3,
        evaluation_mode="MANUAL",
        logged_at=now,
    )

    assert isinstance(log.id, UUID)
    assert log.user_id == user_id
    assert log.question_id == question_id
    assert log.subject_id == subject_id
    assert log.topic_id == topic_id
    assert log.historical_subject_name == "Direito Constitucional"
    assert log.historical_topic_name == "Controle de Constitucionalidade"
    assert log.review_date == today
    assert log.score == 100
    assert log.level_before == 2
    assert log.level_after == 3
    assert log.evaluation_mode == "MANUAL"
    assert log.logged_at == now
    assert log.is_promoted is True
    assert log.is_regressed is False


@pytest.mark.unit
def test_review_audit_log_immutability() -> None:
    """UC-S04-10: Garante que ReviewAuditLog seja estritamente imutável (frozen=True)."""
    log = ReviewAuditLog(
        user_id=uuid4(),
        question_id=uuid4(),
        subject_id=uuid4(),
        topic_id=uuid4(),
        historical_subject_name="História",
        historical_topic_name="Brasil Colônia",
        review_date=date(2026, 10, 7),
        score=100,
        level_before=0,
        level_after=1,
    )

    with pytest.raises(FrozenInstanceError):
        log.score = 50  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        log.historical_subject_name = "Outro Nome"  # type: ignore[misc]


@pytest.mark.unit
def test_review_audit_log_unique_id_generation() -> None:
    """Verifica que instâncias criadas sem ID explícito recebem UUIDs distintos
    (default_factory=uuid4).
    """
    log1 = ReviewAuditLog(
        user_id=uuid4(),
        question_id=uuid4(),
        subject_id=uuid4(),
        topic_id=uuid4(),
        historical_subject_name="Biologia",
        historical_topic_name="Genética",
        review_date=date(2026, 10, 7),
        score=75,
        level_before=1,
        level_after=1,
    )
    log2 = ReviewAuditLog(
        user_id=uuid4(),
        question_id=uuid4(),
        subject_id=uuid4(),
        topic_id=uuid4(),
        historical_subject_name="Biologia",
        historical_topic_name="Genética",
        review_date=date(2026, 10, 7),
        score=75,
        level_before=1,
        level_after=1,
    )
    assert log1.id != log2.id


@pytest.mark.unit
@pytest.mark.parametrize(
    "score,is_promoted,is_regressed",
    [
        (100, True, False),  # Nível 2 -> 3 (Promovido)
        (50, False, False),  # Nível 2 -> 2 (Mantido)
        (0, False, False),  # Nível 2 -> 2 (Mantido)
    ],
)
def test_review_audit_log_promoted_and_maintained_properties(
    score: int, is_promoted: bool, is_regressed: bool
) -> None:
    """UC-S04-01 e UC-S04-29: Verifica propriedades is_promoted e is_regressed."""
    new_level = 3 if score == 100 else 2
    log = ReviewAuditLog(
        user_id=uuid4(),
        question_id=uuid4(),
        subject_id=uuid4(),
        topic_id=uuid4(),
        historical_subject_name="Física",
        historical_topic_name="Cinemática",
        review_date=date(2026, 10, 7),
        score=score,
        level_before=2,
        level_after=new_level,
    )
    assert log.is_promoted is is_promoted
    assert log.is_regressed is is_regressed


@pytest.mark.unit
def test_review_audit_log_regressed_property_level_6_penalty() -> None:
    """UC-S04-28: Verifica penalidade no Nível 6 com is_regressed=True."""
    log = ReviewAuditLog(
        user_id=uuid4(),
        question_id=uuid4(),
        subject_id=uuid4(),
        topic_id=uuid4(),
        historical_subject_name="Química",
        historical_topic_name="Estequiometria",
        review_date=date(2026, 10, 7),
        score=50,
        level_before=6,
        level_after=2,
    )
    assert log.is_promoted is False
    assert log.is_regressed is True


@pytest.mark.unit
@pytest.mark.parametrize("invalid_score", [-1, 101, -100, 999])
def test_review_audit_log_invalid_score_raises_error(invalid_score: int) -> None:
    """UC-S04-11: Rejeita pontuações fora do intervalo [0, 100]."""
    with pytest.raises(DomainValidationError, match="score deve estar entre 0 e 100"):
        ReviewAuditLog(
            user_id=uuid4(),
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Matéria",
            historical_topic_name="Tema",
            review_date=date(2026, 10, 7),
            score=invalid_score,
            level_before=0,
            level_after=0,
        )


@pytest.mark.unit
@pytest.mark.parametrize("invalid_level", [-1, 7, 10, -5])
def test_review_audit_log_invalid_levels_raises_error(invalid_level: int) -> None:
    """UC-S04-11: Rejeita níveis SRS fora do intervalo [0, 6]."""
    with pytest.raises(DomainValidationError, match="level_before deve estar entre 0 e 6"):
        ReviewAuditLog(
            user_id=uuid4(),
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Matéria",
            historical_topic_name="Tema",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=invalid_level,
            level_after=1,
        )

    with pytest.raises(DomainValidationError, match="level_after deve estar entre 0 e 6"):
        ReviewAuditLog(
            user_id=uuid4(),
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Matéria",
            historical_topic_name="Tema",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=1,
            level_after=invalid_level,
        )


@pytest.mark.unit
@pytest.mark.parametrize("invalid_name", ["", "   ", "\t\n"])
def test_review_audit_log_empty_historical_names_raises_error(invalid_name: str) -> None:
    """Rejeita nomes históricos vazios ou contendo apenas espaços em branco."""
    with pytest.raises(DomainValidationError, match="nome histórico da matéria não pode ser vazio"):
        ReviewAuditLog(
            user_id=uuid4(),
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name=invalid_name,
            historical_topic_name="Tema",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=0,
            level_after=1,
        )

    with pytest.raises(DomainValidationError, match="nome histórico do tema não pode ser vazio"):
        ReviewAuditLog(
            user_id=uuid4(),
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Matéria",
            historical_topic_name=invalid_name,
            review_date=date(2026, 10, 7),
            score=100,
            level_before=0,
            level_after=1,
        )


@pytest.mark.unit
@pytest.mark.parametrize("invalid_mode", ["INVALID", "VOICE", "ROBOT", ""])
def test_review_audit_log_invalid_evaluation_mode_raises_error(invalid_mode: str) -> None:
    """Rejeita modos de avaliação não suportados pelo domínio."""
    with pytest.raises(DomainValidationError, match="Modo de avaliação inválido"):
        ReviewAuditLog(
            user_id=uuid4(),
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Matéria",
            historical_topic_name="Tema",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=0,
            level_after=1,
            evaluation_mode=invalid_mode,
        )
