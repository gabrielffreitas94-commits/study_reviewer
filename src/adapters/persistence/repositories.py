"""Implementações concretas dos repositórios utilizando SQLAlchemy 2.0 (Camada 3 - Adaptadores)."""

from uuid import UUID

from sqlalchemy import func, select
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
        stmt = (
            select(SubjectModel.id)
            .where(func.lower(func.trim(SubjectModel.name)) == name.strip().lower())
            .limit(1)
        )
        return self._session.scalar(stmt) is not None


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
        stmt = (
            select(TopicModel.id)
            .where(
                TopicModel.subject_id == subject_id,
                func.lower(func.trim(TopicModel.name)) == name.strip().lower(),
            )
            .limit(1)
        )
        return self._session.scalar(stmt) is not None


class SqlAlchemyFlashcardRepository(IFlashcardRepository):
    """Repositório SQLAlchemy para Flashcards."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, flashcard: Flashcard) -> None:
        model = self._session.get(FlashcardModel, flashcard.id)
        if model is None:
            model = FlashcardMapper.to_model(flashcard)
            self._session.add(model)
        else:
            model.front = flashcard.front
            model.back = flashcard.back
            model.position = flashcard.position
            model.created_at = flashcard.created_at

        if flashcard.topic_ids:
            topics = (
                self._session.query(TopicModel).filter(TopicModel.id.in_(flashcard.topic_ids)).all()
            )
            model.topics = topics

        self._session.commit()

    def save_all(self, flashcards: list[Flashcard]) -> None:
        for card in flashcards:
            model = self._session.get(FlashcardModel, card.id)
            if model is not None:
                model.position = card.position
                model.front = card.front
                model.back = card.back
            else:
                self.save(card)
        self._session.commit()

    def get_by_id(self, flashcard_id: UUID) -> Flashcard | None:
        stmt = select(FlashcardModel).where(FlashcardModel.id == flashcard_id)
        model = self._session.scalars(stmt).first()
        return FlashcardMapper.to_domain(model) if model else None

    def delete(self, flashcard_id: UUID) -> None:
        model = self._session.get(FlashcardModel, flashcard_id)
        if model is not None:
            self._session.delete(model)
            self._session.commit()

    def list_pool(self, subject_id: UUID | None, topic_id: UUID | None) -> list[Flashcard]:
        stmt = select(FlashcardModel).order_by(FlashcardModel.position.asc())

        if topic_id is not None:
            stmt = stmt.join(FlashcardModel.topics).where(TopicModel.id == topic_id)
        elif subject_id is not None:
            stmt = (
                stmt.join(FlashcardModel.topics)
                .where(TopicModel.subject_id == subject_id)
                .distinct()
            )

        models = self._session.scalars(stmt).all()
        return [FlashcardMapper.to_domain(m) for m in models]

    def count_pool(self, subject_id: UUID | None, topic_id: UUID | None) -> int:
        if topic_id is not None:
            stmt = (
                select(func.count(func.distinct(FlashcardModel.id)))
                .join(FlashcardModel.topics)
                .where(TopicModel.id == topic_id)
            )
        elif subject_id is not None:
            stmt = (
                select(func.count(func.distinct(FlashcardModel.id)))
                .join(FlashcardModel.topics)
                .where(TopicModel.subject_id == subject_id)
            )
        else:
            stmt = select(func.count(FlashcardModel.id))

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
