"""Modelos ORM do SQLAlchemy 2.0 para persistência relacional (Camada 3 - Adaptadores)."""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database import Base


class UserModel(Base):
    """Tabela de Usuários."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    google_sub: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    subjects: Mapped[list["SubjectModel"]] = relationship(
        "SubjectModel", back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
    sessions: Mapped[list["PoolSessionModel"]] = relationship(
        "PoolSessionModel", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class SubjectModel(Base):
    """Tabela de Matérias."""

    __tablename__ = "subjects"
    __table_args__ = (
        Index("ix_subjects_id_include_name", "id", postgresql_include=["name"]),
        Index("ix_subjects_owner_public", "owner_id", "is_public"),
        UniqueConstraint("owner_id", "name", name="uq_subject_owner_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    owner: Mapped["UserModel | None"] = relationship("UserModel", back_populates="subjects")
    topics: Mapped[list["TopicModel"]] = relationship(
        "TopicModel", back_populates="subject", cascade="all, delete-orphan", lazy="selectin"
    )


class TopicModel(Base):
    """Tabela de Temas."""

    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("subject_id", "name", name="uq_topic_subject_name"),
        Index(
            "ix_topics_subject_id_include_id_name",
            "subject_id",
            postgresql_include=["id", "name"],
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    subject: Mapped["SubjectModel"] = relationship("SubjectModel", back_populates="topics")
    flashcards: Mapped[list["FlashcardModel"]] = relationship(
        "FlashcardModel",
        secondary="flashcard_topics",
        back_populates="topics",
        lazy="selectin",
    )
    questions: Mapped[list["QuestionModel"]] = relationship(
        "QuestionModel", back_populates="topic", cascade="all, delete-orphan", lazy="selectin"
    )


class FlashcardTopicModel(Base):
    """Tabela associativa N:N entre Flashcards e Temas (ADR-004)."""

    __tablename__ = "flashcard_topics"

    flashcard_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("flashcards.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class FlashcardModel(Base):
    """Tabela de Flashcards com campo de posição para Gap Indexing (ADR-004)."""

    __tablename__ = "flashcards"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    front: Mapped[Text] = mapped_column(Text, nullable=False)
    back: Mapped[Text] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, index=True, default=100)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    topics: Mapped[list["TopicModel"]] = relationship(
        "TopicModel",
        secondary="flashcard_topics",
        back_populates="flashcards",
        lazy="selectin",
    )


class PoolSessionModel(Base):
    """Tabela de Sessões de Estudo persistidas com filtros e progresso."""

    __tablename__ = "flashcard_pool_sessions"
    __table_args__ = (
        Index("ix_sessions_user_filters", "user_id", "subject_id_filter", "topic_id_filter"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, default=uuid4
    )
    subject_id_filter: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True
    )
    topic_id_filter: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    current_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    card_queue: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    user: Mapped["UserModel | None"] = relationship("UserModel", back_populates="sessions")

    def __init__(self, **kwargs: Any) -> None:
        if "card_queue" in kwargs and kwargs["card_queue"]:
            kwargs["card_queue"] = [str(u) for u in kwargs["card_queue"]]
        super().__init__(**kwargs)


FlashcardPoolSessionModel = PoolSessionModel


class StudyEventModel(Base):
    """Tabela de histórico de eventos de estudo com particionamento temporal (append-only)."""

    __tablename__ = "study_events"
    __table_args__ = (
        Index(
            "ix_study_events_user_card_review",
            "user_id",
            "card_id",
            "reviewed_at",
            postgresql_include=["status"],
        ),
    )

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    card_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    session_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 'viewed', 'completed'
    device_id: Mapped[str | None] = mapped_column(String(50), nullable=True)


class QuestionModel(Base):
    """Tabela de Perguntas Abertas (Sprint 03)."""

    __tablename__ = "questions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    topic_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    topic: Mapped["TopicModel"] = relationship("TopicModel", back_populates="questions")
    progresses: Mapped[list["UserQuestionProgressModel"]] = relationship(
        "UserQuestionProgressModel", back_populates="question", cascade="all, delete-orphan"
    )


class UserQuestionProgressModel(Base):
    """Tabela de Progresso SRS de Perguntas Abertas por Estudante (Sprint 03)."""

    __tablename__ = "user_question_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question_progress"),
        Index(
            "ix_user_question_due_covering",
            "user_id",
            "next_review_date",
            postgresql_include=["question_id", "current_level", "last_reviewed_at"],
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    current_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_review_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["UserModel"] = relationship("UserModel")
    question: Mapped["QuestionModel"] = relationship("QuestionModel", back_populates="progresses")


class ReviewAuditLogModel(Base):
    """Tabela de Auditoria Histórica de Revisões de Perguntas Abertas (Sprint 04).

    Imutável e desacoplada: Chaves estrangeiras com ON DELETE SET NULL garantem
    que o histórico e snapshots de nomes permaneçam íntegros mesmo se a matéria,
    tema, pergunta ou usuário forem excluídos (LGPD Art. 16, IV / 18, VI).
    """

    __tablename__ = "review_audit_logs"
    __table_args__ = (
        Index(
            "ix_review_audit_logs_user_date",
            "user_id",
            "review_date",
            postgresql_include=["score", "level_before", "level_after", "logged_at"],
        ),
        Index("ix_review_audit_logs_user_subject", "user_id", "subject_id"),
        Index(
            "ix_review_audit_logs_pagination",
            "user_id",
            "review_date",
            "logged_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subject_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    topic_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True
    )
    historical_subject_name: Mapped[str] = mapped_column(String(100), nullable=False)
    historical_topic_name: Mapped[str] = mapped_column(String(100), nullable=False)
    review_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level_before: Mapped[int] = mapped_column(Integer, nullable=False)
    level_after: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluation_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    user: Mapped["UserModel | None"] = relationship("UserModel")
    question: Mapped["QuestionModel | None"] = relationship("QuestionModel")
    subject: Mapped["SubjectModel | None"] = relationship("SubjectModel")
    topic: Mapped["TopicModel | None"] = relationship("TopicModel")


class KnowledgeSourceModel(Base):
    """Tabela de Fontes/Materiais de Conhecimento vinculados a um Tema."""

    __tablename__ = "knowledge_sources"
    __table_args__ = (Index("ix_knowledge_sources_topic_created", "topic_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    topic_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, default="TEXT")
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    topic: Mapped["TopicModel"] = relationship("TopicModel")
    chunks: Mapped[list["KnowledgeChunkModel"]] = relationship(
        "KnowledgeChunkModel",
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class KnowledgeChunkModel(Base):
    """Tabela de Fragmentos Semânticos Vetorizados de Conhecimento."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_knowledge_chunks_topic", "topic_id"),
        Index("ix_knowledge_chunks_source", "source_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    source: Mapped["KnowledgeSourceModel"] = relationship(
        "KnowledgeSourceModel", back_populates="chunks"
    )
    topic: Mapped["TopicModel"] = relationship("TopicModel")


class TokenLedgerModel(Base):
    """Tabela de Saldos e Retenções de Tokens por Usuário (Sprint 08)."""

    __tablename__ = "token_ledgers"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    held_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    user: Mapped["UserModel"] = relationship("UserModel")


class TokenTransactionModel(Base):
    """Tabela Imutável de Transações do Ledger de Tokens (Sprint 08)."""

    __tablename__ = "token_transactions"
    __table_args__ = (Index("ix_token_transactions_user_created", "user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    user: Mapped["UserModel"] = relationship("UserModel")
