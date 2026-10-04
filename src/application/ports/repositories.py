"""Contratos de repositórios (Portas de Saída - Clean Architecture - Camada 2)."""

from typing import Protocol
from uuid import UUID

from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic, User


class IUserRepository(Protocol):
    """Porta de persistência para Usuários."""

    def save(self, user: User) -> None:
        """Persiste ou atualiza um usuário."""
        ...

    def get_by_id(self, user_id: UUID) -> User | None:
        """Busca um usuário pelo seu UUID primário."""
        ...

    def get_by_google_sub(self, google_sub: str) -> User | None:
        """Busca um usuário pelo seu identificador Google sub."""
        ...

    def get_by_email(self, email: str) -> User | None:
        """Busca um usuário pelo seu endereço de e-mail."""
        ...


class ISubjectRepository(Protocol):
    """Porta de persistência para Matérias."""

    def save(self, subject: Subject) -> None:
        """Persiste ou atualiza uma matéria."""
        ...

    def get_by_id(self, subject_id: UUID) -> Subject | None:
        """Busca uma matéria pelo seu UUID."""
        ...

    def list_all(self) -> list[Subject]:
        """Lista todas as matérias cadastradas."""
        ...

    def list_by_owner(self, owner_id: UUID) -> list[Subject]:
        """Lista todas as matérias pertencentes a um determinado usuário."""
        ...

    def list_accessible(self, user_id: UUID) -> list[Subject]:
        """Lista matérias acessíveis pelo usuário (próprias ou públicas)."""
        ...

    def exists_by_name(self, name: str, owner_id: UUID | None = None) -> bool:
        """Verifica se já existe matéria com o nome informado no escopo do proprietário."""
        ...

    def list_all_with_topics(
        self, user_id: UUID | None = None
    ) -> list[tuple[Subject, list[Topic]]]:
        """Lista matérias acompanhadas de seus respectivos temas em lote (sem N+1)."""
        ...


class ITopicRepository(Protocol):
    """Porta de persistência para Temas."""

    def save(self, topic: Topic) -> None:
        """Persiste ou atualiza um tema."""
        ...

    def get_by_id(self, topic_id: UUID) -> Topic | None:
        """Busca um tema pelo seu UUID."""
        ...

    def list_by_subject(self, subject_id: UUID) -> list[Topic]:
        """Lista todos os temas pertencentes a uma matéria."""
        ...

    def exists_by_name(self, subject_id: UUID, name: str) -> bool:
        """Verifica se já existe tema com o nome no escopo da matéria."""
        ...


class IFlashcardRepository(Protocol):
    """Porta de persistência para Flashcards."""

    def save(self, flashcard: Flashcard) -> None:
        """Persiste ou atualiza um único flashcard."""
        ...

    def save_all(self, flashcards: list[Flashcard]) -> None:
        """Persiste em lote uma lista de flashcards (útil para rebalanceamento e shuffle)."""
        ...

    def get_by_id(self, flashcard_id: UUID) -> Flashcard | None:
        """Busca um flashcard pelo seu UUID."""
        ...

    def delete(self, flashcard_id: UUID) -> None:
        """Exclui permanentemente um flashcard."""
        ...

    def list_pool(
        self,
        subject_id: UUID | None,
        topic_id: UUID | None,
        limit: int | None = None,
        min_position: int | None = None,
    ) -> list[Flashcard]:
        """Lista os cards da pool ordenados por position ASC com filtros opcionais e paginação."""
        ...

    def count_pool(self, subject_id: UUID | None, topic_id: UUID | None) -> int:
        """Retorna o total de cards na pool sob os filtros fornecidos."""
        ...

    def count_by_subjects(self) -> dict[UUID, int]:
        """Retorna contagem de cards agrupados por subject_id em uma única query com GROUP BY."""
        ...

    def count_by_topics(self) -> dict[UUID, int]:
        """Retorna contagem de cards agrupados por topic_id em uma única query com GROUP BY."""
        ...


class ISessionRepository(Protocol):
    """Porta de persistência para o estado das sessões de estudo."""

    def get_active_session(
        self,
        subject_id: UUID | None,
        topic_id: UUID | None,
        user_id: UUID | None = None,
    ) -> FlashcardPoolSession | None:
        """Recupera a sessão ativa para a combinação de filtros e usuário."""
        ...

    def save_session(self, session: FlashcardPoolSession) -> None:
        """Persiste ou atualiza o estado da sessão de estudo."""
        ...
