"""DTOs para Perguntas Abertas e SRS Estrito (Clean Architecture - Camada 2)."""

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CreateQuestionDTO:
    """Dados de entrada para criação de Pergunta Aberta."""

    prompt: str = ""
    expected_answer: str = ""
    topic_ids: tuple[UUID, ...] = ()
    topic_id: UUID | None = None

    def __init__(
        self,
        prompt_or_topic_id: str | UUID = "",
        expected_answer_or_prompt: str = "",
        topic_ids: tuple[UUID, ...] | list[UUID] | None = None,
        topic_id: UUID | None = None,
        prompt: str | None = None,
        expected_answer: str | None = None,
    ) -> None:
        actual_prompt: str = ""
        actual_answer: str = ""
        actual_topic_id: UUID | None = topic_id

        if isinstance(prompt_or_topic_id, UUID):
            actual_topic_id = prompt_or_topic_id
            actual_prompt = expected_answer_or_prompt
            if isinstance(topic_ids, str):
                actual_answer = topic_ids
                topic_ids = None
            elif expected_answer is not None:
                actual_answer = expected_answer
        else:
            actual_prompt = prompt if prompt is not None else str(prompt_or_topic_id)
            actual_answer = (
                expected_answer if expected_answer is not None else str(expected_answer_or_prompt)
            )

        object.__setattr__(self, "prompt", actual_prompt)
        object.__setattr__(self, "expected_answer", actual_answer)

        resolved: tuple[UUID, ...]
        if topic_ids:
            resolved = tuple(topic_ids)
        elif actual_topic_id is not None:
            resolved = (actual_topic_id,)
        else:
            resolved = ()

        object.__setattr__(self, "topic_ids", resolved)
        object.__setattr__(self, "topic_id", resolved[0] if resolved else None)


@dataclass(slots=True, frozen=True)
class UpdateQuestionDTO:
    """Dados de entrada para atualização de Pergunta Aberta."""

    question_id: UUID
    prompt: str
    expected_answer: str


@dataclass(slots=True, frozen=True)
class QuestionDTO:
    """Dados de saída representando uma Pergunta Aberta."""

    id: UUID
    prompt: str
    expected_answer: str
    created_at: date
    topic_ids: tuple[UUID, ...] = ()
    topic_id: UUID | None = None

    def __init__(
        self,
        id: UUID,
        prompt: str = "",
        expected_answer: str = "",
        created_at: date | None = None,
        topic_ids: tuple[UUID, ...] | list[UUID] | None = None,
        topic_id: UUID | None = None,
    ) -> None:
        actual_id = id
        actual_prompt = prompt
        actual_answer = expected_answer
        actual_created_at = created_at or date.today()
        actual_topic_id = topic_id

        if isinstance(prompt, UUID):
            actual_topic_id = prompt
            actual_prompt = expected_answer
            actual_answer = str(created_at) if created_at is not None else ""
            actual_created_at = topic_ids if isinstance(topic_ids, date) else date.today()
            topic_ids = None

        object.__setattr__(self, "id", actual_id)
        object.__setattr__(self, "prompt", actual_prompt)
        object.__setattr__(self, "expected_answer", actual_answer)
        object.__setattr__(self, "created_at", actual_created_at)

        resolved: tuple[UUID, ...]
        if topic_ids:
            resolved = tuple(topic_ids)
        elif actual_topic_id is not None:
            resolved = (actual_topic_id,)
        else:
            resolved = ()

        object.__setattr__(self, "topic_ids", resolved)
        object.__setattr__(self, "topic_id", resolved[0] if resolved else None)

    @classmethod
    def from_entity(cls, entity: Any) -> "QuestionDTO":
        return cls(
            id=entity.id,
            topic_ids=entity.topic_ids,
            topic_id=entity.topic_id,
            prompt=entity.prompt,
            expected_answer=entity.expected_answer,
            created_at=entity.created_at,
        )


@dataclass(slots=True, frozen=True)
class DueQuestionItemDTO:
    """Item da fila de perguntas vencidas para revisão do dia."""

    question_id: UUID
    subject_name: str
    topic_name: str
    prompt: str
    expected_answer: str
    current_level: int
    interval_days: int
    due_date: date


@dataclass(slots=True, frozen=True)
class ReviewQuestionInputDTO:
    """Entrada da submissão de nota pelo estudante."""

    question_id: UUID
    score: int


@dataclass(slots=True, frozen=True)
class ReviewQuestionResultDTO:
    """Resultado processado pelo motor SRS após a revisão."""

    question_id: UUID
    previous_level: int
    new_level: int
    next_review_date: date
    interval_days: int
    is_promoted: bool
    is_regressed: bool
