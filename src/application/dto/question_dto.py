"""DTOs para Perguntas Abertas e SRS Estrito (Clean Architecture - Camada 2)."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CreateQuestionDTO:
    """Dados de entrada para criação de Pergunta Aberta."""

    topic_id: UUID
    prompt: str
    expected_answer: str


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
    topic_id: UUID
    prompt: str
    expected_answer: str
    created_at: date


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
