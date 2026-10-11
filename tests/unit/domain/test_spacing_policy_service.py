"""Testes unitários para o motor SpacingPolicyService (Sprint 03)."""

from datetime import date

import pytest

from src.domain.exceptions import DomainValidationError, InvalidScoreError
from src.domain.services import SpacingPolicyService


@pytest.mark.unit
@pytest.mark.parametrize(
    ("current_level", "expected_new_level", "expected_days"),
    [
        (0, 1, 7),
        (1, 2, 15),
        (2, 3, 30),
        (3, 4, 60),
        (4, 5, 90),
        (5, 6, 180),
        (6, 6, 180),  # Teto do nível 6
    ],
)
def test_spacing_policy_promotion_with_perfect_score(
    current_level: int, expected_new_level: int, expected_days: int
) -> None:
    """Verifica avanço estrito de nível quando score == 100."""
    review_date = date(2026, 10, 10)
    new_level, next_date = SpacingPolicyService.calculate_next_schedule(
        current_level=current_level, score=100, review_date=review_date
    )

    assert new_level == expected_new_level
    delta = (next_date - review_date).days
    assert delta == expected_days


@pytest.mark.unit
@pytest.mark.parametrize(
    ("current_level", "score", "expected_days"),
    [
        (0, 99, 1),
        (0, 50, 1),
        (0, 0, 1),
        (1, 99, 7),
        (1, 75, 7),
        (2, 50, 15),
        (3, 25, 30),
        (4, 0, 60),
        (5, 99, 90),
    ],
)
def test_spacing_policy_retention_when_score_below_100_levels_0_to_5(
    current_level: int, score: int, expected_days: int
) -> None:
    """Verifica que pontuações < 100 mantêm o nível atual nos níveis 0 a 5."""
    review_date = date(2026, 10, 10)
    new_level, next_date = SpacingPolicyService.calculate_next_schedule(
        current_level=current_level, score=score, review_date=review_date
    )

    assert new_level == current_level
    delta = (next_date - review_date).days
    assert delta == expected_days


@pytest.mark.unit
@pytest.mark.parametrize("score", [99, 75, 50, 25, 1, 0])
def test_spacing_policy_level_6_penalty_regression(score: int) -> None:
    """Verifica a penalidade de regressão severa no nível 6 quando score < 100."""
    review_date = date(2026, 10, 10)
    new_level, next_date = SpacingPolicyService.calculate_next_schedule(
        current_level=6, score=score, review_date=review_date
    )

    # Queda estrita para o Nível 2 (+15 dias)
    assert new_level == 2
    delta = (next_date - review_date).days
    assert delta == 15
    assert next_date == date(2026, 10, 25)


@pytest.mark.unit
def test_spacing_policy_overdue_card_calculates_from_real_review_date() -> None:
    """Verifica que cards atrasados calculam a nova data a partir de review_date (hoje)."""
    # Card estava agendado para 2026-08-01 (atrasado), respondido hoje em 2026-10-10
    review_date = date(2026, 10, 10)
    new_level, next_date = SpacingPolicyService.calculate_next_schedule(
        current_level=2, score=100, review_date=review_date
    )

    assert new_level == 3
    assert next_date == date(2026, 11, 9)  # 2026-10-10 + 30 dias


@pytest.mark.unit
def test_spacing_policy_leap_year_and_year_rollover() -> None:
    """Verifica cálculos através de viradas de mês bissexto e viradas de ano."""
    # Ano bissexto 2028-02-28 + 1 dia
    _, next_date_leap = SpacingPolicyService.calculate_next_schedule(
        current_level=0, score=50, review_date=date(2028, 2, 28)
    )
    assert next_date_leap == date(2028, 2, 29)

    # Virada de ano 2026-12-15 + 30 dias (Nível 2 -> 3)
    _, next_date_year = SpacingPolicyService.calculate_next_schedule(
        current_level=2, score=100, review_date=date(2026, 12, 15)
    )
    assert next_date_year == date(2027, 1, 14)


@pytest.mark.unit
@pytest.mark.parametrize("invalid_score", [-1, -50, 101, 200])
def test_spacing_policy_invalid_score_raises_error(invalid_score: int) -> None:
    """Verifica rejeição de notas fora do intervalo fechado [0, 100]."""
    with pytest.raises(InvalidScoreError, match="A nota deve estar entre 0 e 100"):
        SpacingPolicyService.calculate_next_schedule(
            current_level=1, score=invalid_score, review_date=date(2026, 10, 10)
        )


@pytest.mark.unit
@pytest.mark.parametrize("invalid_level", [-1, 7, 10])
def test_spacing_policy_invalid_level_raises_error(invalid_level: int) -> None:
    """Verifica rejeição de níveis fora do intervalo [0, 6]."""
    with pytest.raises(DomainValidationError, match="O nível atual deve estar entre 0 e 6"):
        SpacingPolicyService.calculate_next_schedule(
            current_level=invalid_level, score=100, review_date=date(2026, 10, 10)
        )


@pytest.mark.unit
@pytest.mark.security
def test_spacing_policy_security_boundary_isolation() -> None:
    """Vulnerabilidade prevenida: Manipulação indevida de intervalos do SRS e injeção de parâmetros.
    Garantia de segurança: Constante INTERVALS é tupla imutável protegida contra mutação em runtime.
    """
    assert isinstance(SpacingPolicyService.INTERVALS, tuple)
    with pytest.raises(TypeError):
        SpacingPolicyService.INTERVALS[0] = 999  # type: ignore[index]


@pytest.mark.unit
def test_spacing_policy_get_interval() -> None:
    """Verifica retorno correto de intervalos para diferentes níveis com clamp nos extremos."""
    assert SpacingPolicyService.get_interval(0) == 1
    assert SpacingPolicyService.get_interval(1) == 7
    assert SpacingPolicyService.get_interval(2) == 15
    assert SpacingPolicyService.get_interval(3) == 30
    assert SpacingPolicyService.get_interval(4) == 60
    assert SpacingPolicyService.get_interval(5) == 90
    assert SpacingPolicyService.get_interval(6) == 180
    # Clamping fora dos limites
    assert SpacingPolicyService.get_interval(-1) == 1
    assert SpacingPolicyService.get_interval(99) == 180
