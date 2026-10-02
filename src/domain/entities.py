"""Entidades de domínio puras do sistema Study Reviewer (Clean Architecture - Camada 1)."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from src.domain.exceptions import DomainValidationError


@dataclass
class Subject:
    """Entidade que representa uma Matéria macro de estudo."""

    name: str
    id: UUID = field(default_factory=uuid4)
    created_at: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if len(self.name) < 2 or len(self.name) > 100:
            raise DomainValidationError("Nome da matéria deve ter entre 2 e 100 caracteres.")


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
    """Entidade que representa um Flashcard com posição de Gap Indexing."""

    topic_id: UUID
    front: str
    back: str
    position: int = 100
    id: UUID = field(default_factory=uuid4)
    created_at: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        self.front = self.front.strip()
        self.back = self.back.strip()

        if len(self.front) < 1 or len(self.front) > 5000:
            raise DomainValidationError("Frente do flashcard deve ter entre 1 e 5.000 caracteres.")

        if len(self.back) < 1 or len(self.back) > 10000:
            raise DomainValidationError("Verso do flashcard deve ter entre 1 e 10.000 caracteres.")

        if self.position < 1:
            raise DomainValidationError(
                "Posição do flashcard deve ser um inteiro positivo maior ou igual a 1."
            )


@dataclass
class FlashcardPoolSession:
    """Entidade que encapsula o estado persistido de uma sessão de estudo da pool."""

    id: UUID = field(default_factory=uuid4)
    subject_id_filter: UUID | None = None
    topic_id_filter: UUID | None = None
    current_position: int = 0
    round_number: int = 1
    is_active: bool = True
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.round_number < 1:
            raise DomainValidationError("Número da rodada deve ser maior ou igual a 1.")

    def advance_to(self, position: int) -> None:
        """Avança o ponteiro de exibição para uma nova posição."""
        self.current_position = position
        self.updated_at = datetime.now(UTC)

    def next_round(self, initial_position: int = 100) -> None:
        """Incrementa a rodada e redefine o ponteiro para o primeiro card."""
        self.round_number += 1
        self.current_position = initial_position
        self.updated_at = datetime.now(UTC)
