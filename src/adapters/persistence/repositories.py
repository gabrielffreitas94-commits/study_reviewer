"""Implementações concretas dos repositórios utilizando SQLAlchemy 2.0 (Camada 3 - Adaptadores)."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from src.adapters.persistence.mappers import (
    FlashcardMapper,
    SessionMapper,
    SubjectMapper,
    TopicMapper,
    UserMapper,
)
from src.adapters.persistence.models import (
    FlashcardModel,
    FlashcardTopicModel,
    PoolSessionModel,
    StudyEventModel,
    SubjectModel,
    TopicModel,
    UserModel,
)
from src.application.ports.repositories import (
    IFlashcardRepository,
    ISessionRepository,
    IStudyEventRepository,
    ISubjectRepository,
    ITopicRepository,
    IUserRepository,
)
from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic, User


class SqlAlchemyUserRepository(IUserRepository):
    """Repositório SQLAlchemy para Usuários."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, user: User) -> None:
        model = UserMapper.to_model(user)
        self._session.merge(model)
        self._session.commit()

    def get_by_id(self, user_id: UUID) -> User | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        model = self._session.scalars(stmt).first()
        return UserMapper.to_domain(model) if model else None

    def get_by_google_sub(self, google_sub: str) -> User | None:
        stmt = select(UserModel).where(UserModel.google_sub == google_sub.strip())
        model = self._session.scalars(stmt).first()
        return UserMapper.to_domain(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(
            func.lower(func.trim(UserModel.email)) == email.strip().lower()
        )
        model = self._session.scalars(stmt).first()
        return UserMapper.to_domain(model) if model else None


class SqlAlchemySubjectRepository(ISubjectRepository):
    """Repositório SQLAlchemy para Matérias com suporte a multi-tenancy e acesso público."""

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

    def list_by_owner(self, owner_id: UUID) -> list[Subject]:
        stmt = (
            select(SubjectModel)
            .where(SubjectModel.owner_id == owner_id)
            .order_by(func.lower(SubjectModel.name).asc())
        )
        models = self._session.scalars(stmt).all()
        return [SubjectMapper.to_domain(m) for m in models]

    def list_accessible(self, user_id: UUID) -> list[Subject]:
        stmt = (
            select(SubjectModel)
            .where(
                or_(
                    SubjectModel.owner_id == user_id,
                    SubjectModel.is_public.is_(True),
                )
            )
            .order_by(func.lower(SubjectModel.name).asc())
        )
        models = self._session.scalars(stmt).all()
        return [SubjectMapper.to_domain(m) for m in models]

    def exists_by_name(self, name: str, owner_id: UUID | None = None) -> bool:
        stmt = select(SubjectModel.id).where(
            func.lower(func.trim(SubjectModel.name)) == name.strip().lower()
        )
        if owner_id is not None:
            stmt = stmt.where(SubjectModel.owner_id == owner_id)
        stmt = stmt.limit(1)
        return self._session.scalar(stmt) is not None

    def list_all_with_topics(
        self, user_id: UUID | None = None
    ) -> list[tuple[Subject, list[Topic]]]:
        stmt = (
            select(SubjectModel)
            .options(selectinload(SubjectModel.topics))
            .order_by(func.lower(SubjectModel.name).asc())
        )
        if user_id is not None:
            stmt = stmt.where(
                or_(
                    SubjectModel.owner_id == user_id,
                    SubjectModel.is_public.is_(True),
                )
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
        model = FlashcardMapper.to_model(flashcard)
        self._session.merge(model)
        self._session.commit()

        # Atualiza a tabela associativa N:N (flashcard_topics)
        self._session.query(FlashcardTopicModel).filter(
            FlashcardTopicModel.flashcard_id == flashcard.id
        ).delete()

        for t_id in flashcard.topic_ids:
            assoc = FlashcardTopicModel(flashcard_id=flashcard.id, topic_id=t_id)
            self._session.add(assoc)

        self._session.commit()

    def save_all(self, flashcards: list[Flashcard]) -> None:
        if not flashcards:
            return

        models = [FlashcardMapper.to_model(c) for c in flashcards]
        card_ids = [c.id for c in flashcards]

        self._session.query(FlashcardTopicModel).filter(
            FlashcardTopicModel.flashcard_id.in_(card_ids)
        ).delete(synchronize_session=False)

        new_assocs = [
            FlashcardTopicModel(flashcard_id=c.id, topic_id=t_id)
            for c in flashcards
            for t_id in c.topic_ids
        ]

        for m in models:
            self._session.merge(m)
        self._session.bulk_save_objects(new_assocs)
        self._session.commit()

    def get_by_id(self, flashcard_id: UUID) -> Flashcard | None:
        stmt = (
            select(FlashcardModel)
            .options(selectinload(FlashcardModel.topics))
            .where(FlashcardModel.id == flashcard_id)
        )
        model = self._session.scalars(stmt).first()
        return FlashcardMapper.to_domain(model) if model else None

    def delete(self, flashcard_id: UUID) -> None:
        stmt = select(FlashcardModel).where(FlashcardModel.id == flashcard_id)
        model = self._session.scalars(stmt).first()
        if model:
            self._session.delete(model)
            self._session.commit()

    def list_pool(
        self,
        subject_id: UUID | None,
        topic_id: UUID | None,
        limit: int | None = None,
        min_position: int | None = None,
    ) -> list[Flashcard]:
        stmt = select(FlashcardModel).options(selectinload(FlashcardModel.topics))
        stmt = stmt.order_by(FlashcardModel.position.asc())

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
        self,
        subject_id: UUID | None,
        topic_id: UUID | None,
        user_id: UUID | None = None,
    ) -> FlashcardPoolSession | None:
        stmt = select(PoolSessionModel).where(
            PoolSessionModel.subject_id_filter == subject_id,
            PoolSessionModel.topic_id_filter == topic_id,
            PoolSessionModel.is_active.is_(True),
        )
        if user_id is not None:
            stmt = stmt.where(PoolSessionModel.user_id == user_id)
        model = self._session.scalars(stmt).first()
        return SessionMapper.to_domain(model) if model else None

    def get_by_id(self, session_id: UUID) -> FlashcardPoolSession | None:
        stmt = select(PoolSessionModel).where(PoolSessionModel.id == session_id)
        model = self._session.scalars(stmt).first()
        return SessionMapper.to_domain(model) if model else None

    def save_session(self, session: FlashcardPoolSession) -> None:
        model = SessionMapper.to_model(session)
        self._session.merge(model)
        self._session.commit()


class SqlAlchemyStudyEventRepository(IStudyEventRepository):
    """Repositório SQLAlchemy para histórico append-only de eventos de estudo (study_events)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert(self, events: list[dict[str, Any]]) -> int:
        if not events:
            return 0

        bind = self._session.get_bind()
        dialect_name = bind.dialect.name if bind else "sqlite"

        insert_stmt: Any
        if dialect_name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            insert_stmt = (
                pg_insert(StudyEventModel)
                .values(events)
                .on_conflict_do_nothing(index_elements=["reviewed_at", "user_id", "id"])
            )
        else:
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            insert_stmt = (
                sqlite_insert(StudyEventModel)
                .values(events)
                .on_conflict_do_nothing(index_elements=["reviewed_at", "user_id", "id"])
            )

        res: Any = self._session.execute(insert_stmt)
        self._session.commit()
        rowcount = getattr(res, "rowcount", -1)
        return int(rowcount) if rowcount != -1 else len(events)

    def list_by_user(self, user_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
        stmt = (
            select(StudyEventModel)
            .where(StudyEventModel.user_id == user_id)
            .order_by(StudyEventModel.reviewed_at.desc())
            .limit(limit)
        )
        models = self._session.scalars(stmt).all()
        return [
            {
                "id": m.id,
                "reviewed_at": m.reviewed_at,
                "user_id": m.user_id,
                "card_id": m.card_id,
                "session_id": m.session_id,
                "status": m.status,
                "device_id": m.device_id,
            }
            for m in models
        ]

    def anonymize_user_events(self, user_id: UUID) -> int:
        stmt = (
            update(StudyEventModel)
            .where(StudyEventModel.user_id == user_id)
            .values(user_id=None, device_id=None)
        )
        res: Any = self._session.execute(stmt)
        self._session.commit()
        rowcount = getattr(res, "rowcount", -1)
        return int(rowcount) if rowcount != -1 else 0
