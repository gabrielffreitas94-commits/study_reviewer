"""Modelos ORM do SQLAlchemy 2.0 para persistência relacional (Camada 3 - Adaptadores)."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database import Base


class SubjectModel(Base):
    """Tabela de Matérias."""

    __tablename__ = "subjects"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    topics: Mapped[list["TopicModel"]] = relationship(
        "TopicModel", back_populates="subject", cascade="all, delete-orphan"
    )


class TopicModel(Base):
    """Tabela de Temas."""

    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("subject_id", "name", name="uq_topic_subject_name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    subject: Mapped["SubjectModel"] = relationship("SubjectModel", back_populates="topics")
    flashcards: Mapped[list["FlashcardModel"]] = relationship(
        "FlashcardModel", back_populates="topic", cascade="all, delete-orphan"
    )


class FlashcardModel(Base):
    """Tabela de Flashcards com campo de posição para Gap Indexing."""

    __tablename__ = "flashcards"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    topic_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, index=True, default=100)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)

    topic: Mapped["TopicModel"] = relationship("TopicModel", back_populates="flashcards")


class PoolSessionModel(Base):
    """Tabela de Sessões de Estudo persistidas com filtros e progresso."""

    __tablename__ = "flashcard_pool_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
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
