"""Entidades de domínio puras do sistema Study Reviewer (Clean Architecture - Camada 1)."""

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from src.domain.exceptions import (
    DomainValidationError,
    EmptyKnowledgeContentError,
    InsufficientTokensError,
    InvalidEmailError,
    InvalidEmbeddingError,
    InvalidExpectedAnswerError,
    InvalidGoogleSubError,
    InvalidPromptError,
)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


@dataclass
class User:
    """Entidade que representa um Usuário/Estudante autenticado."""

    google_sub: str
    email: str
    name: str
    avatar_url: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        self.google_sub = self.google_sub.strip() if self.google_sub is not None else ""
        self.email = self.email.strip().lower() if self.email is not None else ""
        self.name = self.name.strip() if self.name is not None else ""
        if self.avatar_url is not None:
            cleaned_avatar = self.avatar_url.strip()
            self.avatar_url = cleaned_avatar if cleaned_avatar else None

        if not self.google_sub:
            raise InvalidGoogleSubError("O identificador Google (sub) não pode ser vazio.")

        if not self.name or len(self.name) > 150:
            raise DomainValidationError("Nome de usuário deve ter entre 1 e 150 caracteres.")

        if not self._is_valid_email(self.email):
            raise InvalidEmailError(f"Formato de e-mail inválido: '{self.email}'.")

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        return bool(EMAIL_REGEX.match(email))


@dataclass
class Subject:
    """Entidade que representa uma Matéria macro de estudo com suporte
    a multi-tenancy e compartilhamento read-only.
    """

    name: str
    id: UUID = field(default_factory=uuid4)
    owner_id: UUID = field(default_factory=uuid4)
    is_public: bool = False
    created_at: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if len(self.name) < 2 or len(self.name) > 100:
            raise DomainValidationError("Nome da matéria deve ter entre 2 e 100 caracteres.")

    def can_be_edited_by(self, user_id: UUID | None) -> bool:
        """Determina se o usuário possui permissão de edição/exclusão (apenas o proprietário)."""
        if user_id is None:
            return False
        return self.owner_id == user_id

    def can_be_studied_by(self, user_id: UUID | None) -> bool:
        """Determina se o usuário possui permissão de estudo (proprietário ou matéria pública)."""
        if user_id is not None and self.owner_id == user_id:
            return True
        return self.is_public


@dataclass
class Topic:
    """Entidade que representa um Tema/Tópico pertencente a uma Matéria."""

    subject_id: UUID
    name: str
    id: UUID = field(default_factory=uuid4)
    created_at: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if len(self.name) < 2 or len(self.name) > 100:
            raise DomainValidationError("Nome do tema deve ter entre 2 e 100 caracteres.")


@dataclass
class Flashcard:
    """Entidade que representa um Flashcard com suporte a múltiplos temas (ADR-004)."""

    front: str
    back: str
    topic_ids: tuple[UUID, ...] = field(default_factory=tuple)
    position: int = 100
    id: UUID = field(default_factory=uuid4)
    created_at: date = field(default_factory=date.today)

    def __init__(
        self,
        front: str,
        back: str,
        topic_ids: tuple[UUID, ...] | list[UUID] | None = None,
        position: int = 100,
        id: UUID | None = None,
        created_at: date | None = None,
        topic_id: UUID | None = None,
    ) -> None:
        self.front = front.strip() if front is not None else ""
        self.back = back.strip() if back is not None else ""
        self.position = position
        self.id = id if id is not None else uuid4()
        self.created_at = created_at if created_at is not None else date.today()

        resolved_topics: tuple[UUID, ...]
        if topic_ids is not None:
            resolved_topics = tuple(topic_ids)
        elif topic_id is not None:
            resolved_topics = (topic_id,)
        else:
            resolved_topics = ()

        self.topic_ids = resolved_topics

        if not self.topic_ids or len(self.topic_ids) < 1:
            raise DomainValidationError("Flashcard deve estar associado a pelo menos 1 tema.")

        if len(self.topic_ids) > 5:
            raise DomainValidationError("Flashcard pode estar associado a no máximo 5 temas.")

        if len(set(self.topic_ids)) != len(self.topic_ids):
            raise DomainValidationError("Flashcard não pode conter temas duplicados.")

        if len(self.front) < 1 or len(self.front) > 5000:
            raise DomainValidationError("Frente do flashcard deve ter entre 1 e 5.000 caracteres.")

        if len(self.back) < 1 or len(self.back) > 10000:
            raise DomainValidationError("Verso do flashcard deve ter entre 1 e 10.000 caracteres.")

        if self.position < 1:
            raise DomainValidationError(
                "Posição do flashcard deve ser um inteiro positivo maior ou igual a 1."
            )

    @property
    def primary_topic_id(self) -> UUID:
        """Retorna o tema principal (primeiro) do flashcard."""
        return self.topic_ids[0]

    @property
    def topic_id(self) -> UUID:
        """Propriedade de compatibilidade retornando o primeiro tema associado."""
        return self.topic_ids[0]

    def update_content(self, front: str, back: str) -> None:
        """Atualiza frente e verso do flashcard aplicando validações de domínio."""
        clean_front = front.strip() if front is not None else ""
        clean_back = back.strip() if back is not None else ""
        if len(clean_front) < 1 or len(clean_front) > 5000:
            raise DomainValidationError("Frente do flashcard deve ter entre 1 e 5.000 caracteres.")
        if len(clean_back) < 1 or len(clean_back) > 10000:
            raise DomainValidationError("Verso do flashcard deve ter entre 1 e 10.000 caracteres.")
        self.front = clean_front
        self.back = clean_back


@dataclass(slots=True)
class FlashcardPoolSession:
    """Entidade de domínio rica representando a sessão efêmera de estudo.

    A fila `card_queue` contém exclusivamente a fatia da rodada ativa
    (50 a 100 UUIDs), otimizando o consumo de RAM em larga escala.
    """

    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    subject_id: UUID | None = None
    topic_id_filter: UUID | None = None
    round_number: int = 1
    current_index: int = 0  # Cursor na fila (0 a N-1)
    card_queue: list[UUID] = field(default_factory=list)  # Janela ativa da rodada
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Campos e métodos de compatibilidade (Depreciados: programados para remoção na Sprint 03)
    subject_id_filter: UUID | None = None  # Depreciado: use `subject_id`
    current_position: int = 0  # Depreciado: use `current_index` com `card_queue`
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.subject_id is None and self.subject_id_filter is not None:
            self.subject_id = self.subject_id_filter
        elif self.subject_id_filter is None and self.subject_id is not None:
            self.subject_id_filter = self.subject_id

        if self.current_index < 0:
            raise DomainValidationError("O índice atual não pode ser negativo.")
        if self.round_number < 1:
            raise DomainValidationError("O número da rodada deve ser >= 1.")

    def get_current_card_id(self) -> UUID | None:
        if self.current_index < len(self.card_queue):
            return self.card_queue[self.current_index]
        return None

    def advance(self) -> None:
        self.current_index += 1
        self.updated_at = datetime.now(UTC)

    def is_round_finished(self) -> bool:
        return self.current_index >= len(self.card_queue)

    def start_new_round(self, shuffled_ids: list[UUID]) -> None:
        if not shuffled_ids:
            raise DomainValidationError("A nova rodada requer uma lista não-vazia de IDs.")
        self.round_number += 1
        self.card_queue = list(shuffled_ids)
        self.current_index = 0
        self.updated_at = datetime.now(UTC)

    def advance_to(self, position: int) -> None:
        """[DEPRECIADO: Remoção Sprint 03] Avança o ponteiro de exibição para nova posição."""
        self.current_position = position
        self.updated_at = datetime.now(UTC)

    def next_round(self, initial_position: int = 100) -> None:
        """[DEPRECIADO: Remoção na Sprint 03] Incrementa a rodada e redefine o ponteiro."""
        self.round_number += 1
        self.current_position = initial_position
        self.current_index = 0
        self.updated_at = datetime.now(UTC)


@dataclass(slots=True)
class Question:
    """Entidade que representa uma Pergunta Aberta pertencente a um Tema."""

    topic_id: UUID
    prompt: str
    expected_answer: str
    id: UUID = field(default_factory=uuid4)
    created_at: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        self.prompt = self.prompt.strip() if self.prompt is not None else ""
        self.expected_answer = (
            self.expected_answer.strip() if self.expected_answer is not None else ""
        )
        if not self.prompt or len(self.prompt) > 10_000:
            raise InvalidPromptError("Enunciado deve ter entre 1 e 10.000 caracteres.")
        if not self.expected_answer or len(self.expected_answer) > 10_000:
            raise InvalidExpectedAnswerError("Gabarito deve ter entre 1 e 10.000 caracteres.")


@dataclass(slots=True)
class UserQuestionProgress:
    """Entidade que representa o progresso individual de um Estudante no motor SRS."""

    user_id: UUID
    question_id: UUID
    current_level: int = 0
    next_review_date: date = field(default_factory=date.today)
    last_reviewed_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not (0 <= self.current_level <= 6):
            raise DomainValidationError("O nível SRS deve estar estritamente entre 0 e 6.")

    def apply_review(self, new_level: int, next_date: date, reviewed_at: datetime) -> None:
        """Aplica a transição calculada pelo SpacingPolicyService preservando invariantes."""
        if not (0 <= new_level <= 6):
            raise DomainValidationError("O nível SRS deve pertencer ao intervalo [0, 6].")
        self.current_level = new_level
        self.next_review_date = next_date
        self.last_reviewed_at = reviewed_at


@dataclass(slots=True, frozen=True)
class ReviewAuditLog:
    """Entidade indelével representando uma tentativa de revisão de pergunta aberta.

    Preserva snapshot textual congelado da matéria e do tema no instante da avaliação,
    garantindo imunidade analítica a edições ou exclusões posteriores do catálogo.
    """

    user_id: UUID | None
    question_id: UUID | None
    subject_id: UUID | None
    topic_id: UUID | None
    historical_subject_name: str
    historical_topic_name: str
    review_date: date
    score: int
    level_before: int
    level_after: int
    evaluation_mode: str = "MANUAL"
    logged_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not (0 <= self.score <= 100):
            raise DomainValidationError(f"O score deve estar entre 0 e 100. Recebido: {self.score}")
        if not (0 <= self.level_before <= 6):
            raise DomainValidationError(
                f"O level_before deve estar entre 0 e 6. Recebido: {self.level_before}"
            )
        if not (0 <= self.level_after <= 6):
            raise DomainValidationError(
                f"O level_after deve estar entre 0 e 6. Recebido: {self.level_after}"
            )
        if not self.historical_subject_name or not self.historical_subject_name.strip():
            raise DomainValidationError("O nome histórico da matéria não pode ser vazio.")
        if not self.historical_topic_name or not self.historical_topic_name.strip():
            raise DomainValidationError("O nome histórico do tema não pode ser vazio.")
        if self.evaluation_mode not in ("MANUAL", "AI_TEXT", "AI_AUDIO", "MULTIAGENT_DISPUTE"):
            raise DomainValidationError(f"Modo de avaliação inválido: {self.evaluation_mode}")

    @property
    def is_promoted(self) -> bool:
        return self.level_after > self.level_before

    @property
    def is_regressed(self) -> bool:
        return self.level_after < self.level_before


@dataclass(slots=True)
class KnowledgeSource:
    """Entidade que representa um material/fonte de conhecimento associado a um Tema."""

    topic_id: UUID
    title: str
    content_type: str = "TEXT"  # TEXT, SUMMARY, BOOK_CHAPTER
    total_chunks: int = 0
    char_count: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        self.title = self.title.strip() if self.title is not None else ""
        if len(self.title) < 2 or len(self.title) > 200:
            raise DomainValidationError("Título do material deve ter entre 2 e 200 caracteres.")
        if self.total_chunks < 0:
            raise DomainValidationError("total_chunks não pode ser negativo.")
        if self.char_count < 0:
            raise DomainValidationError("char_count não pode ser negativo.")


@dataclass(slots=True)
class KnowledgeChunk:
    """Entidade que representa um fragmento semântico de conhecimento vetorizado."""

    source_id: UUID
    topic_id: UUID
    chunk_index: int
    content: str
    embedding: tuple[float, ...] = field(default_factory=tuple)
    token_estimate: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        self.content = self.content.strip() if self.content is not None else ""
        if not self.content:
            raise EmptyKnowledgeContentError("Conteúdo do chunk não pode ser vazio.")
        if self.chunk_index < 0:
            raise DomainValidationError("Índice do chunk não pode ser negativo.")
        if not self.embedding:
            raise InvalidEmbeddingError("Vetor de embedding não pode ser vazio.")


@dataclass(slots=True, frozen=True)
class ValidationResult:
    """Entidade de valor representando o resultado da validação de uma questão contra a base RAG."""

    is_grounded: bool
    confidence_score: float
    evidence_chunk_ids: tuple[UUID, ...]
    evidence_quotes: tuple[str, ...]
    reasoning: str
    suggested_improvements: tuple[str, ...]

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence_score <= 1.0):
            raise DomainValidationError("confidence_score deve estar entre 0.0 e 1.0.")


@dataclass(slots=True)
class TokenLedger:
    """Entidade que controla o saldo e a retenção em duas fases de tokens do usuário."""

    user_id: UUID
    balance: int = 1000
    held_balance: int = 0
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.balance < 0:
            raise DomainValidationError("O saldo de tokens não pode ser negativo.")
        if self.held_balance < 0:
            raise DomainValidationError("O saldo retido de tokens não pode ser negativo.")
        if self.held_balance > self.balance:
            raise DomainValidationError("O saldo retido não pode exceder o saldo total.")

    @property
    def available_balance(self) -> int:
        return self.balance - self.held_balance

    def hold(self, amount: int) -> None:
        if amount <= 0:
            raise DomainValidationError("A quantidade para retenção deve ser positiva.")
        if self.available_balance < amount:
            raise InsufficientTokensError(
                f"Saldo insuficiente de tokens. Disponível: {self.available_balance}, "
                f"Solicitado: {amount}"
            )
        self.held_balance += amount
        self.updated_at = datetime.now(UTC)

    def settle(self, hold_amount: int, actual_tokens: int) -> None:
        if hold_amount <= 0 or actual_tokens < 0:
            raise DomainValidationError("Valores de liquidação inválidos.")
        if hold_amount > self.held_balance:
            raise DomainValidationError("A retenção a liberar excede o saldo atualmente retido.")
        self.held_balance -= hold_amount
        self.balance = max(0, self.balance - actual_tokens)
        self.updated_at = datetime.now(UTC)

    def refund_hold(self, amount: int) -> None:
        if amount <= 0:
            raise DomainValidationError("A quantidade para estorno deve ser positiva.")
        if amount > self.held_balance:
            raise DomainValidationError("A quantidade de estorno excede o saldo retido.")
        self.held_balance -= amount
        self.updated_at = datetime.now(UTC)

    def deposit(self, amount: int) -> None:
        if amount <= 0:
            raise DomainValidationError("A quantidade de depósito deve ser positiva.")
        self.balance += amount
        self.updated_at = datetime.now(UTC)


@dataclass(slots=True, frozen=True)
class TokenTransaction:
    """Entidade indelével registrando uma movimentação financeira no ledger de tokens."""

    user_id: UUID
    transaction_type: str  # DEPOSIT, HOLD, SETTLEMENT, REFUND
    amount: int
    reference_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise DomainValidationError("O montante da transação não pode ser negativo.")
        if self.transaction_type not in ("DEPOSIT", "HOLD", "SETTLEMENT", "REFUND"):
            raise DomainValidationError(f"Tipo de transação inválido: {self.transaction_type}")


@dataclass(slots=True, frozen=True)
class AnswerEvaluationResult:
    """Resultado estruturado e auditável da avaliação semântica de uma resposta aberta."""

    score: int
    feedback: str
    coverage_score: int = 100
    accuracy_score: int = 100
    depth_score: int = 100
    evidence_quotes: tuple[str, ...] = ()
    tokens_used: int = 0
    cached_context: bool = False
    evaluation_mode: str = "AI_TEXT"
    transcribed_text: str | None = None

    def __post_init__(self) -> None:
        if not (0 <= self.score <= 100):
            raise DomainValidationError("O score de avaliação deve estar entre 0 e 100.")
        if not (0 <= self.coverage_score <= 100):
            raise DomainValidationError("O coverage_score deve estar entre 0 e 100.")
        if not (0 <= self.accuracy_score <= 100):
            raise DomainValidationError("O accuracy_score deve estar entre 0 e 100.")
        if not (0 <= self.depth_score <= 100):
            raise DomainValidationError("O depth_score deve estar entre 0 e 100.")
        if self.tokens_used < 0:
            raise DomainValidationError("Tokens consumidos não podem ser negativos.")
        if not self.feedback or not self.feedback.strip():
            raise DomainValidationError("Feedback de avaliação não pode ser vazio.")
        if self.evaluation_mode not in ("AI_TEXT", "AI_AUDIO", "MULTIAGENT_DISPUTE"):
            raise DomainValidationError(f"Modo de avaliação inválido: {self.evaluation_mode}")


@dataclass(slots=True, frozen=True)
class DisputeEvaluationResult:
    """Resultado deliberado pelo conselho multiagente na contestação de avaliação."""

    status: str  # "UPHELD" ou "REJECTED"
    revised_score: int
    advocate_rationale: str
    critic_rationale: str
    arbitrator_verdict: str
    tokens_used: int = 0
    refund_dispute_tokens: bool = False

    def __post_init__(self) -> None:
        if self.status not in ("UPHELD", "REJECTED"):
            raise DomainValidationError(f"Status de contestação inválido: {self.status}")
        if not (0 <= self.revised_score <= 100):
            raise DomainValidationError("O revised_score deve estar entre 0 e 100.")
        if not self.advocate_rationale or not self.advocate_rationale.strip():
            raise DomainValidationError("O parecer do advogado não pode ser vazio.")
        if not self.critic_rationale or not self.critic_rationale.strip():
            raise DomainValidationError("O parecer do crítico não pode ser vazio.")
        if not self.arbitrator_verdict or not self.arbitrator_verdict.strip():
            raise DomainValidationError("O veredito do árbitro não pode ser vazio.")
        if self.tokens_used < 0:
            raise DomainValidationError("Tokens consumidos não podem ser negativos.")
