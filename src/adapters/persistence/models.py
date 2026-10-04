"""Modelos ORM do SQLAlchemy 2.0 para persistência relacional (Camada 3 - Adaptadores)."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
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
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    user: Mapped["UserModel | None"] = relationship("UserModel", back_populates="sessions")
