"""Implementações concretas dos repositórios utilizando SQLAlchemy 2.0 (Camada 3 - Adaptadores)."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.adapters.persistence.mappers import (
    FlashcardMapper,
    SessionMapper,
    SubjectMapper,
    TopicMapper,
)
from src.adapters.persistence.models import (
    FlashcardModel,
    PoolSessionModel,
    SubjectModel,
    TopicModel,
)
from src.application.ports.repositories import (
    IFlashcardRepository,
    ISessionRepository,
    ISubjectRepository,
    ITopicRepository,
)
from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic


class SqlAlchemySubjectRepository(ISubjectRepository):
    """Repositório SQLAlchemy para Matérias."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, subject: Subject) -> None:
        model = SubjectMapper.to_model(subject)
        self._session.merge(model)
        self._session.commit()

    def get_by_id(self, subject_id: UUID) -> Subject | None:
        stmt = select(SubjectModel).where(SubjectModel.id == subject_id)
        model = self._session.scalars(stmt).first()
        return SubjectMapper.to_domain(model) if model else None

    def list_all(self) -> list[Subject]:
        stmt = select(SubjectModel).order_by(func.lower(SubjectModel.name).asc())
        models = self._session.scalars(stmt).all()
        return [SubjectMapper.to_domain(m) for m in models]

    def exists_by_name(self, name: str) -> bool:
        stmt = select(SubjectModel.name)
        names = self._session.scalars(stmt).all()
        norm = name.strip().lower()
        return any(n.strip().lower() == norm for n in names)


class SqlAlchemyTopicRepository(ITopicRepository):
    """Repositório SQLAlchemy para Temas."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, topic: Topic) -> None:
        model = TopicMapper.to_model(topic)
        self._session.merge(model)
        self._session.commit()

    def get_by_id(self, topic_id: UUID) -> Topic | None:
        stmt = select(TopicModel).where(TopicModel.id == topic_id)
        model = self._session.scalars(stmt).first()
        return TopicMapper.to_domain(model) if model else None

    def list_by_subject(self, subject_id: UUID) -> list[Topic]:
        stmt = (
            select(TopicModel)
            .where(TopicModel.subject_id == subject_id)
            .order_by(TopicModel.name.asc())
        )
        models = self._session.scalars(stmt).all()
        return [TopicMapper.to_domain(m) for m in models]

    def exists_by_name(self, subject_id: UUID, name: str) -> bool:
        stmt = select(TopicModel.name).where(TopicModel.subject_id == subject_id)
        names = self._session.scalars(stmt).all()
        norm = name.strip().lower()
        return any(n.strip().lower() == norm for n in names)


class SqlAlchemyFlashcardRepository(IFlashcardRepository):
    """Repositório SQLAlchemy para Flashcards."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, flashcard: Flashcard) -> None:
        model = FlashcardMapper.to_model(flashcard)
        self._session.merge(model)
        self._session.commit()

    def save_all(self, flashcards: list[Flashcard]) -> None:
        for card in flashcards:
            model = FlashcardMapper.to_model(card)
            self._session.merge(model)
        self._session.commit()

    def get_by_id(self, flashcard_id: UUID) -> Flashcard | None:
        stmt = select(FlashcardModel).where(FlashcardModel.id == flashcard_id)
        model = self._session.scalars(stmt).first()
        return FlashcardMapper.to_domain(model) if model else None

    def delete(self, flashcard_id: UUID) -> None:
        stmt = delete(FlashcardModel).where(FlashcardModel.id == flashcard_id)
        self._session.execute(stmt)
        self._session.commit()

    def list_pool(self, subject_id: UUID | None, topic_id: UUID | None) -> list[Flashcard]:
        stmt = select(FlashcardModel).order_by(FlashcardModel.position.asc())

        if topic_id is not None:
            stmt = stmt.where(FlashcardModel.topic_id == topic_id)
        elif subject_id is not None:
            stmt = stmt.join(TopicModel).where(TopicModel.subject_id == subject_id)

        models = self._session.scalars(stmt).all()
        return [FlashcardMapper.to_domain(m) for m in models]

    def count_pool(self, subject_id: UUID | None, topic_id: UUID | None) -> int:
        stmt = select(func.count(FlashcardModel.id))

        if topic_id is not None:
            stmt = stmt.where(FlashcardModel.topic_id == topic_id)
        elif subject_id is not None:
            stmt = stmt.join(TopicModel).where(TopicModel.subject_id == subject_id)

        count = self._session.scalar(stmt)
        return count or 0


class SqlAlchemySessionRepository(ISessionRepository):
    """Repositório SQLAlchemy para Sessões de Estudo."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_active_session(
        self, subject_id: UUID | None, topic_id: UUID | None
    ) -> FlashcardPoolSession | None:
        stmt = select(PoolSessionModel).where(
            PoolSessionModel.subject_id_filter == subject_id,
            PoolSessionModel.topic_id_filter == topic_id,
            PoolSessionModel.is_active.is_(True),
        )
        model = self._session.scalars(stmt).first()
        return SessionMapper.to_domain(model) if model else None

    def save_session(self, session: FlashcardPoolSession) -> None:
        model = SessionMapper.to_model(session)
        self._session.merge(model)
        self._session.commit()
