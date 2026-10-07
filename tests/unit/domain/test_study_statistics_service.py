"""Testes unitários para o serviço de domínio StudyStatisticsCalculatorService (Sprint 04)."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from src.domain.entities import ReviewAuditLog, UserQuestionProgress
from src.domain.services import StudyStatisticsCalculatorService


@pytest.mark.unit
def test_calculate_statistics_nominal() -> None:
    """UC-S04-02: Calcula estatísticas nominais com retenção, nível 4+ e distribuição."""
    user_id = uuid4()
    d1 = date(2026, 10, 5)
    d2 = date(2026, 10, 6)
    d3 = date(2026, 10, 7)

    # 4 revisões: 3 com score 100, 1 com score 50 -> retenção 75.0%
    logs = [
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Direito",
            historical_topic_name="Constitucional",
            review_date=d1,
            score=100,
            level_before=1,
            level_after=2,
        ),
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Direito",
            historical_topic_name="Constitucional",
            review_date=d2,
            score=100,
            level_before=3,
            level_after=4,
        ),
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Informática",
            historical_topic_name="Redes",
            review_date=d3,
            score=50,
            level_before=2,
            level_after=2,
        ),
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Informática",
            historical_topic_name="Redes",
            review_date=d3,
            score=100,
            level_before=4,
            level_after=5,
        ),
    ]

    # 5 progressos atuais do estudante: 2 no Nível 4+, 1 no Nível 2, 2 no Nível 0
    progresses = [
        UserQuestionProgress(user_id=user_id, question_id=uuid4(), current_level=4),
        UserQuestionProgress(user_id=user_id, question_id=uuid4(), current_level=5),
        UserQuestionProgress(user_id=user_id, question_id=uuid4(), current_level=2),
        UserQuestionProgress(user_id=user_id, question_id=uuid4(), current_level=0),
        UserQuestionProgress(user_id=user_id, question_id=uuid4(), current_level=0),
    ]

    stats = StudyStatisticsCalculatorService.compute_metrics(logs=logs, progresses=progresses)

    assert stats.total_reviews_count == 4
    assert stats.retention_rate == 75.0
    assert stats.mature_questions_count == 2
    assert stats.active_days_count == 3
    assert stats.srs_distribution == {0: 2, 1: 0, 2: 1, 3: 0, 4: 1, 5: 1, 6: 0}


@pytest.mark.unit
def test_calculate_statistics_empty_state() -> None:
    """UC-S04-05: Trata histórico vazio sem divisão por zero."""
    stats = StudyStatisticsCalculatorService.compute_metrics(logs=[], progresses=[])

    assert stats.total_reviews_count == 0
    assert stats.retention_rate == 0.0
    assert stats.mature_questions_count == 0
    assert stats.active_days_count == 0
    assert stats.srs_distribution == {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    assert stats.subject_performances == []
    assert stats.mature_evolution_timeline == []


@pytest.mark.unit
def test_calculate_subject_performances() -> None:
    """Calcula taxas de acerto agrupadas por matéria histórica."""
    user_id = uuid4()
    logs = [
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Matemática",
            historical_topic_name="Álgebra",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=0,
            level_after=1,
        ),
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Matemática",
            historical_topic_name="Geometria",
            review_date=date(2026, 10, 7),
            score=100,
            level_before=1,
            level_after=2,
        ),
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Português",
            historical_topic_name="Sintaxe",
            review_date=date(2026, 10, 7),
            score=50,
            level_before=1,
            level_after=1,
        ),
    ]

    perfs = StudyStatisticsCalculatorService.compute_subject_performances(logs)
    perfs_by_name = {p.subject_name: p for p in perfs}

    assert "Matemática" in perfs_by_name
    assert perfs_by_name["Matemática"].total_reviews == 2
    assert perfs_by_name["Matemática"].retention_rate == 100.0

    assert "Português" in perfs_by_name
    assert perfs_by_name["Português"].total_reviews == 1
    assert perfs_by_name["Português"].retention_rate == 0.0


@pytest.mark.unit
def test_calculate_mature_evolution_timeline() -> None:
    """UC-S04-06: Gera série temporal de promoções para Retenção Madura (Nível 4+)."""
    user_id = uuid4()
    d1 = date(2026, 10, 1)
    d2 = date(2026, 10, 3)

    logs = [
        # Promoção para Nível 4 em d1
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Direito",
            historical_topic_name="Tributário",
            review_date=d1,
            score=100,
            level_before=3,
            level_after=4,
        ),
        # Promoção simples N1 -> N2 (não entra em N4+)
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Direito",
            historical_topic_name="Tributário",
            review_date=d1,
            score=100,
            level_before=1,
            level_after=2,
        ),
        # Promoção para Nível 5 em d2
        ReviewAuditLog(
            user_id=user_id,
            question_id=uuid4(),
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Direito",
            historical_topic_name="Tributário",
            review_date=d2,
            score=100,
            level_before=4,
            level_after=5,
        ),
    ]

    timeline = StudyStatisticsCalculatorService.compute_mature_timeline(logs)
    assert len(timeline) >= 2
    assert timeline[0].date == d1
    assert timeline[0].mature_count == 1
    assert timeline[1].date == d2
    assert timeline[1].mature_count == 2


@pytest.mark.unit
def test_calculate_mature_evolution_timeline_with_regression() -> None:
    """UC-S04-28: Verifica queda na linha do tempo quando um card maduro regride (N6 -> N2)."""
    user_id = uuid4()
    q_id = uuid4()
    d1 = date(2026, 10, 1)
    d2 = date(2026, 10, 2)

    logs = [
        ReviewAuditLog(
            user_id=user_id,
            question_id=q_id,
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Direito",
            historical_topic_name="Constitucional",
            review_date=d1,
            score=100,
            level_before=5,
            level_after=6,
        ),
        ReviewAuditLog(
            user_id=user_id,
            question_id=q_id,
            subject_id=uuid4(),
            topic_id=uuid4(),
            historical_subject_name="Direito",
            historical_topic_name="Constitucional",
            review_date=d2,
            score=50,
            level_before=6,
            level_after=2,
        ),
    ]

    timeline = StudyStatisticsCalculatorService.compute_mature_timeline(logs)
    assert len(timeline) == 2
    assert timeline[0].date == d1
    assert timeline[0].mature_count == 1
    assert timeline[1].date == d2
    assert timeline[1].mature_count == 0

