"""Contratos de repositórios (Portas de Saída - Clean Architecture - Camada 2)."""

from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

from src.application.dto.question_dto import DueQuestionItemDTO
from src.domain.entities import (
    Flashcard,
    FlashcardPoolSession,
    KnowledgeChunk,
    KnowledgeSource,
    Question,
    ReviewAuditLog,
    Subject,
    TokenLedger,
    TokenTransaction,
    Topic,
    User,
    UserQuestionProgress,
)


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

    def delete(self, user_id: UUID) -> None:
        """Remove um usuário pelo seu identificador único."""
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
        offset: int | None = None,
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

    def get_by_id(self, session_id: UUID) -> FlashcardPoolSession | None:
        """Recupera uma sessão de estudo pelo seu UUID."""
        ...

    def save_session(self, session: FlashcardPoolSession) -> None:
        """Persiste ou atualiza o estado da sessão de estudo."""
        ...


class IStudyEventRepository(Protocol):
    """Porta para histórico append-only de eventos de estudo (study_events)."""

    def bulk_insert(self, events: list[dict[str, Any]]) -> int:
        """Insere lote de eventos com idempotência (ON CONFLICT DO NOTHING)."""
        ...

    def list_by_user(self, user_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
        """Lista eventos históricos de um usuário ordenados cronologicamente."""
        ...

    def anonymize_user_events(self, user_id: UUID) -> int:
        """Anonimiza eventos desvinculando user_id e device_id (LGPD Art. 16, IV / 18, VI)."""
        ...


class IQuestionRepository(Protocol):
    """Porta de persistência para o Catálogo de Perguntas Abertas."""

    def save(self, question: Question) -> None:
        """Persiste ou atualiza uma pergunta no catálogo."""
        ...

    def get_by_id(self, question_id: UUID) -> Question | None:
        """Busca uma pergunta pelo seu UUID primário."""
        ...

    def list_by_topic(self, topic_id: UUID) -> list[Question]:
        """Lista todas as perguntas pertencentes a um determinado tema."""
        ...

    def delete(self, question_id: UUID) -> None:
        """Exclui permanentemente uma pergunta do catálogo."""
        ...


class IQuestionProgressRepository(Protocol):
    """Porta de persistência para o Histórico e Progresso Individual no SRS."""

    def save(self, progress: UserQuestionProgress) -> None:
        """Persiste ou atualiza o progresso individual de uma pergunta."""
        ...

    def get_by_user_and_question(
        self, user_id: UUID, question_id: UUID
    ) -> UserQuestionProgress | None:
        """Busca o registro de progresso para a combinação de usuário e pergunta."""
        ...

    def get_due_questions(
        self,
        user_id: UUID,
        reference_date: date,
        subject_id: UUID | None = None,
        topic_id: UUID | None = None,
        limit: int = 50,
    ) -> list[DueQuestionItemDTO]:
        """Retorna a fila de perguntas pendentes para a data informada em consulta única sem N+1."""
        ...

    def count_due_questions(self, user_id: UUID, reference_date: date) -> int:
        """Retorna o total de perguntas pendentes para o badge dinâmico."""
        ...

    def get_next_review_date(self, user_id: UUID, reference_date: date) -> date | None:
        """Retorna a data de vencimento mais próxima estritamente superior a reference_date."""
        ...

    def initialize_progress_for_questions(
        self, user_id: UUID, question_ids: list[UUID], initial_date: date
    ) -> None:
        """Inicializa em lote o progresso de perguntas para um estudante (JIT seguro)."""
        ...

    def list_by_user(self, user_id: UUID) -> list[UserQuestionProgress]:
        """Lista todos os registros de progresso de um estudante."""
        ...


class IReviewAuditRepository(Protocol):
    """Porta de persistência para a Trilha de Auditoria Histórica de Revisões (Sprint 04)."""

    def save(self, log: ReviewAuditLog) -> None:
        """Persiste um registro indelével de auditoria."""
        ...

    def list_by_user(
        self, user_id: UUID, limit: int = 50, offset: int = 0, subject_id: UUID | None = None
    ) -> list[ReviewAuditLog]:
        """Retorna logs paginados do estudante com filtro opcional por matéria."""
        ...

    def count_by_user(self, user_id: UUID, subject_id: UUID | None = None) -> int:
        """Retorna o total de revisões realizadas pelo estudante."""
        ...

    def get_all_by_user(self, user_id: UUID) -> list[ReviewAuditLog]:
        """Retorna todos os logs do estudante."""
        ...

    def stream_by_user(self, user_id: UUID, chunk_size: int = 1000) -> Any:
        """Retorna gerador de logs com consumo de memória O(1) para exportação massiva."""
        ...

    def get_active_dates_count(self, user_id: UUID) -> int:
        """Retorna a contagem de datas distintas em que o estudante realizou revisões."""
        ...


class IUnitOfWork(Protocol):
    """Porta para controle transacional ACID atômico."""

    def commit(self) -> None:
        """Persiste atomicamente as operações da transação."""
        ...

    def rollback(self) -> None:
        """Reverte todas as operações não commitadas."""
        ...


class IClockService(Protocol):
    """Porta para serviços temporais desacoplados para facilidade de testes."""

    def today(self) -> date:
        """Retorna a data corrente de calendário."""
        ...

    def now(self) -> datetime:
        """Retorna o timestamp corrente com fuso horário."""
        ...


class IKnowledgeSourceRepository(Protocol):
    """Porta de persistência para Fontes de Conhecimento (Materiais Didáticos)."""

    def save(self, source: KnowledgeSource) -> KnowledgeSource:
        """Persiste ou atualiza uma fonte de conhecimento."""
        ...

    def get_by_id(self, source_id: UUID) -> KnowledgeSource | None:
        """Busca uma fonte de conhecimento pelo seu identificador primário."""
        ...

    def list_by_topic(self, topic_id: UUID) -> list[KnowledgeSource]:
        """Lista todas as fontes de conhecimento vinculadas a um tema."""
        ...

    def delete(self, source_id: UUID) -> bool:
        """Remove uma fonte de conhecimento."""
        ...


class IKnowledgeChunkRepository(Protocol):
    """Porta de persistência para Fragmentos Vetoriais de Conhecimento (Chunks)."""

    def save_batch(self, chunks: list[KnowledgeChunk]) -> None:
        """Persiste uma lista de chunks de conhecimento em lote."""
        ...

    def list_by_topic(self, topic_id: UUID) -> list[KnowledgeChunk]:
        """Lista todos os chunks de conhecimento de um tema."""
        ...

    def delete_by_source(self, source_id: UUID) -> int:
        """Remove todos os chunks associados a uma fonte específica."""
        ...

    def search_similar(
        self,
        topic_id: UUID,
        query_embedding: list[float] | tuple[float, ...],
        top_k: int = 5,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """Busca os top-k chunks mais relevantes de um tema por similaridade de cosseno."""
        ...


class ITokenLedgerRepository(Protocol):
    """Porta de persistência para o saldo e transações de tokens do usuário."""

    def get_by_user_id(self, user_id: UUID, for_update: bool = False) -> TokenLedger | None:
        """Recupera o saldo/ledger de tokens do usuário."""
        ...

    def save(self, ledger: TokenLedger) -> TokenLedger:
        """Persiste ou atualiza o saldo/ledger de tokens."""
        ...

    def record_transaction(self, transaction: TokenTransaction) -> TokenTransaction:
        """Registra uma movimentação no extrato/ledger de tokens."""
        ...

    def list_transactions(self, user_id: UUID, limit: int = 50) -> list[TokenTransaction]:
        """Lista as transações mais recentes do usuário ordenadas por data descendente."""
        ...
