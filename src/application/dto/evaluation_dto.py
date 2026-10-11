"""DTOs para avaliação semântica aterrada de respostas e tarifação de tokens."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EvaluateAnswerInputDTO:
    """Dados de entrada para avaliação de resposta dissertativa com IA."""

    question_id: UUID
    student_answer: str


@dataclass(frozen=True, slots=True)
class EvaluateAnswerResponseDTO:
    """Resultado completo da avaliação de resposta com métricas pedagógicas e tarifação."""

    question_id: UUID
    score: int
    feedback: str
    coverage_score: int
    accuracy_score: int
    depth_score: int
    evidence_quotes: list[str]
    level_before: int
    level_after: int
    next_review_date: date
    tokens_deducted: int
    remaining_token_balance: int
    evaluation_mode: str = "AI_TEXT"
    transcribed_text: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluateAudioAnswerInputDTO:
    """Dados de entrada para avaliação de resposta em áudio com IA multimodal."""

    question_id: UUID
    audio_bytes: bytes
    mime_type: str = "audio/webm"


@dataclass(frozen=True, slots=True)
class DisputeEvaluationInputDTO:
    """Dados de entrada para contestação de avaliação perante o conselho multiagente."""

    question_id: UUID
    student_answer: str
    dispute_argument: str


@dataclass(frozen=True, slots=True)
class DisputeEvaluationResponseDTO:
    """Resultado deliberado pelo conselho multiagente na contestação de avaliação."""

    question_id: UUID
    status: str
    previous_score: int
    revised_score: int
    advocate_rationale: str
    critic_rationale: str
    arbitrator_verdict: str
    level_before: int
    level_after: int
    next_review_date: date
    tokens_deducted: int
    remaining_token_balance: int
    refund_dispute_tokens: bool = False


@dataclass(frozen=True, slots=True)
class UserTokenBalanceDTO:
    """Saldo atual de tokens do estudante no ledger."""

    user_id: UUID
    balance: int
    held_balance: int
    available_balance: int


@dataclass(frozen=True, slots=True)
class DepositTokensInputDTO:
    """Entrada para recarga de créditos de tokens."""

    amount: int


@dataclass(frozen=True, slots=True)
class TokenTransactionDTO:
    """Registro de transação financeira no extrato de tokens."""

    id: UUID
    transaction_type: str
    amount: int
    reference_id: str | None
    created_at: datetime
