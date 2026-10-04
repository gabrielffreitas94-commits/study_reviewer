"""Entidades de domínio puras do sistema Study Reviewer (Clean Architecture - Camada 1)."""

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from src.domain.exceptions import (
    DomainValidationError,
    InvalidEmailError,
    InvalidGoogleSubError,
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

    def can_be_edited_by(self, user_id: UUID) -> bool:
        """Determina se o usuário possui permissão de edição/exclusão (apenas o proprietário)."""
        return self.owner_id == user_id

    def can_be_studied_by(self, user_id: UUID) -> bool:
        """Determina se o usuário possui permissão de estudo (proprietário ou matéria pública)."""
        return self.owner_id == user_id or self.is_public


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


@dataclass
class FlashcardPoolSession:
    """Entidade que encapsula o estado persistido de uma sessão de estudo da pool."""

    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
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
