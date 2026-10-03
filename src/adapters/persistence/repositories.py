"""Implementações concretas dos repositórios utilizando SQLAlchemy 2.0 (Camada 3 - Adaptadores)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.adapters.persistence.mappers import (
    FlashcardMapper,
    SessionMapper,
    SubjectMapper,
    TopicMapper,
)
from src.adapters.persistence.models import (
    FlashcardModel,
    FlashcardTopicModel,
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

    def list_all_with_topics(self) -> list[tuple[Subject, list[Topic]]]:
        stmt = (
            select(SubjectModel)
            .options(selectinload(SubjectModel.topics))
            .order_by(func.lower(SubjectModel.name).asc())
        )
        models = self._session.scalars(stmt).all()
        return [
            (
                SubjectMapper.to_domain(m),
                [
                    TopicMapper.to_domain(t)
                    for t in sorted(m.topics, key=lambda top: top.name.lower())
                ],
            )
            for m in models
        ]


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
            if flashcard.topic_ids:
                stmt = select(TopicModel).where(TopicModel.id.in_(flashcard.topic_ids))
                model.topics = list(self._session.scalars(stmt).all())
            self._session.add(model)
        else:
            model.front = flashcard.front
            model.back = flashcard.back
            model.position = flashcard.position
            model.created_at = flashcard.created_at

            if flashcard.topic_ids:
                current_topic_ids = {t.id for t in model.topics}
                if current_topic_ids != set(flashcard.topic_ids):
                    stmt = select(TopicModel).where(TopicModel.id.in_(flashcard.topic_ids))
                    model.topics = list(self._session.scalars(stmt).all())

        self._session.commit()

    def save_all(self, flashcards: list[Flashcard]) -> None:
        if not flashcards:
            return

        card_ids = [card.id for card in flashcards]
        stmt = select(FlashcardModel).where(FlashcardModel.id.in_(card_ids))
        existing_models = {m.id: m for m in self._session.scalars(stmt).all()}

        new_cards: list[Flashcard] = []
        for card in flashcards:
            model = existing_models.get(card.id)
            if model is not None:
                model.position = card.position
                model.front = card.front
                model.back = card.back
            else:
                new_cards.append(card)

        if new_cards:
            all_topic_ids = {t_id for c in new_cards for t_id in c.topic_ids}
            topics_map: dict[UUID, TopicModel] = {}
            if all_topic_ids:
                topic_models = self._session.scalars(
                    select(TopicModel).where(TopicModel.id.in_(all_topic_ids))
                ).all()
                topics_map = {t.id: t for t in topic_models}

            new_models: list[FlashcardModel] = []
            for card in new_cards:
                m = FlashcardMapper.to_model(card)
                if card.topic_ids:
                    m.topics = [topics_map[t_id] for t_id in card.topic_ids if t_id in topics_map]
                new_models.append(m)

            self._session.add_all(new_models)

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

    def list_pool(
        self,
        subject_id: UUID | None,
        topic_id: UUID | None,
        limit: int | None = None,
        min_position: int | None = None,
    ) -> list[Flashcard]:
        stmt = select(FlashcardModel).order_by(FlashcardModel.position.asc())

        if min_position is not None:
            stmt = stmt.where(FlashcardModel.position > min_position)

        if topic_id is not None:
            stmt = stmt.join(FlashcardModel.topics).where(TopicModel.id == topic_id)
        elif subject_id is not None:
            stmt = (
                stmt.join(FlashcardModel.topics)
                .where(TopicModel.subject_id == subject_id)
                .distinct()
            )

        if limit is not None:
            stmt = stmt.limit(limit)

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

    def count_by_subjects(self) -> dict[UUID, int]:
        stmt = (
            select(
                TopicModel.subject_id,
                func.count(func.distinct(FlashcardTopicModel.flashcard_id)),
            )
            .join(TopicModel, FlashcardTopicModel.topic_id == TopicModel.id)
            .group_by(TopicModel.subject_id)
        )
        rows = self._session.execute(stmt).all()
        return {sub_id: count for sub_id, count in rows if sub_id is not None}

    def count_by_topics(self) -> dict[UUID, int]:
        stmt = select(
            FlashcardTopicModel.topic_id,
            func.count(FlashcardTopicModel.flashcard_id),
        ).group_by(FlashcardTopicModel.topic_id)
        rows = self._session.execute(stmt).all()
        return {top_id: count for top_id, count in rows if top_id is not None}


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
