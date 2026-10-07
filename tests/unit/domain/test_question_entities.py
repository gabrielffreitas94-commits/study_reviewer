"""Testes unitários para as entidades Question e UserQuestionProgress (Sprint 03)."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from src.domain.entities import Question, UserQuestionProgress
from src.domain.exceptions import (
    DomainValidationError,
    InvalidExpectedAnswerError,
    InvalidPromptError,
)


@pytest.mark.unit
def test_question_creation_valid() -> None:
    """Verifica a instanciação válida de Question com trimming."""
    topic_id = uuid4()
    q = Question(
        topic_id=topic_id,
        prompt="  O que é Clean Architecture?  ",
        expected_answer="  É uma arquitetura de software centrada no domínio.  ",
    )
    assert isinstance(q.id, UUID)
    assert q.topic_id == topic_id
    assert q.prompt == "O que é Clean Architecture?"
    assert q.expected_answer == "É uma arquitetura de software centrada no domínio."
    assert isinstance(q.created_at, date)


@pytest.mark.unit
@pytest.mark.parametrize("invalid_prompt", ["", "   ", "x" * 10001])
def test_question_invalid_prompt_raises_error(invalid_prompt: str) -> None:
    """Verifica rejeição de enunciados vazios ou excedendo 10.000 caracteres."""
    with pytest.raises(InvalidPromptError):
        Question(
            topic_id=uuid4(),
            prompt=invalid_prompt,
            expected_answer="Resposta válida",
        )


@pytest.mark.unit
@pytest.mark.parametrize("invalid_answer", ["", "   ", "y" * 10001])
def test_question_invalid_expected_answer_raises_error(invalid_answer: str) -> None:
    """Verifica rejeição de respostas esperadas vazias ou excedendo 10.000 caracteres."""
    with pytest.raises(InvalidExpectedAnswerError):
        Question(
            topic_id=uuid4(),
            prompt="Pergunta válida",
            expected_answer=invalid_answer,
        )


@pytest.mark.unit
def test_question_boundary_lengths() -> None:
    """Verifica limites extremos de 1 e 10.000 caracteres."""
    q_min = Question(topic_id=uuid4(), prompt="A", expected_answer="B")
    assert q_min.prompt == "A"
    assert q_min.expected_answer == "B"

    prompt_max = "P" * 10000
    answer_max = "R" * 10000
    q_max = Question(topic_id=uuid4(), prompt=prompt_max, expected_answer=answer_max)
    assert len(q_max.prompt) == 10000
    assert len(q_max.expected_answer) == 10000


@pytest.mark.unit
def test_user_question_progress_defaults() -> None:
    """Verifica criação com valores padrão do progresso individual."""
    user_id = uuid4()
    question_id = uuid4()
    prog = UserQuestionProgress(user_id=user_id, question_id=question_id)

    assert isinstance(prog.id, UUID)
    assert prog.user_id == user_id
    assert prog.question_id == question_id
    assert prog.current_level == 0
    assert prog.next_review_date == date.today()
    assert prog.last_reviewed_at is None


@pytest.mark.unit
@pytest.mark.parametrize("invalid_level", [-1, 7, 10, -5])
def test_user_question_progress_invalid_level_raises_error(invalid_level: int) -> None:
    """Verifica rejeição de níveis fora do intervalo [0, 6]."""
    with pytest.raises(
        DomainValidationError, match="O nível SRS deve estar estritamente entre 0 e 6"
    ):
        UserQuestionProgress(
            user_id=uuid4(),
            question_id=uuid4(),
            current_level=invalid_level,
        )


@pytest.mark.unit
def test_user_question_progress_apply_review_valid() -> None:
    """Verifica o método de domínio rico apply_review."""
    prog = UserQuestionProgress(user_id=uuid4(), question_id=uuid4(), current_level=1)
    now = datetime.now(UTC)
    next_d = date(2026, 10, 25)

    prog.apply_review(new_level=2, next_date=next_d, reviewed_at=now)

    assert prog.current_level == 2
    assert prog.next_review_date == next_d
    assert prog.last_reviewed_at == now


@pytest.mark.unit
@pytest.mark.parametrize("invalid_level", [-1, 7, 99])
def test_user_question_progress_apply_review_invalid_level_raises_error(invalid_level: int) -> None:
    """Verifica que apply_review valida o novo nível estritamente."""
    prog = UserQuestionProgress(user_id=uuid4(), question_id=uuid4(), current_level=1)
    now = datetime.now(UTC)
    next_d = date(2026, 10, 25)

    with pytest.raises(DomainValidationError, match="O nível SRS deve pertencer ao intervalo"):
        prog.apply_review(new_level=invalid_level, next_date=next_d, reviewed_at=now)


@pytest.mark.unit
@pytest.mark.security
def test_question_immutability_and_slots() -> None:
    """Vulnerabilidade prevenida: Consumo descontrolado de memória e injeção dinâmica.

    Garantia de segurança: Entidades com slots=True previnem criação indevida de __dict__.
    """
    q = Question(topic_id=uuid4(), prompt="P", expected_answer="R")
    with pytest.raises(AttributeError):
        q.injected_attribute = "malicious"  # type: ignore[attr-defined]

    prog = UserQuestionProgress(user_id=uuid4(), question_id=uuid4())
    with pytest.raises(AttributeError):
        prog.injected_attribute = "malicious"  # type: ignore[attr-defined]
