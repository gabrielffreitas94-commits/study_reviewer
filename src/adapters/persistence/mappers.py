"""Mappers bidirecionais entre entidades puras de domínio e modelos ORM (Camada 3 - Adaptadores)."""

from src.adapters.persistence.models import (
    FlashcardModel,
    PoolSessionModel,
    SubjectModel,
    TopicModel,
    UserModel,
)
from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic, User


class UserMapper:
    """Conversor para Usuário."""

    @staticmethod
    def to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            google_sub=model.google_sub,
            email=model.email,
            name=model.name,
            avatar_url=model.avatar_url,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: User) -> UserModel:
        return UserModel(
            id=entity.id,
            google_sub=entity.google_sub,
            email=entity.email,
            name=entity.name,
            avatar_url=entity.avatar_url,
            created_at=entity.created_at,
        )


class SubjectMapper:
    """Conversor para Matéria."""

    @staticmethod
    def to_domain(model: SubjectModel) -> Subject:
        return Subject(
            id=model.id,
            name=model.name,
            owner_id=model.owner_id,
            is_public=model.is_public,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Subject) -> SubjectModel:
        return SubjectModel(
            id=entity.id,
            name=entity.name,
            owner_id=entity.owner_id,
            is_public=entity.is_public,
            created_at=entity.created_at,
        )


class TopicMapper:
    """Conversor para Tema."""

    @staticmethod
    def to_domain(model: TopicModel) -> Topic:
        return Topic(
            id=model.id,
            subject_id=model.subject_id,
            name=model.name,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Topic) -> TopicModel:
        return TopicModel(
            id=entity.id,
            subject_id=entity.subject_id,
            name=entity.name,
            created_at=entity.created_at,
        )


class FlashcardMapper:
    """Conversor para Flashcard (ADR-004)."""

    @staticmethod
    def to_domain(model: FlashcardModel) -> Flashcard:
        topic_ids = tuple(t.id for t in model.topics) if model.topics else ()
        return Flashcard(
            id=model.id,
            topic_ids=topic_ids,
            front=str(model.front),
            back=str(model.back),
            position=model.position,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Flashcard) -> FlashcardModel:
        return FlashcardModel(
            id=entity.id,
            front=entity.front,
            back=entity.back,
            position=entity.position,
            created_at=entity.created_at,
        )


class SessionMapper:
    """Conversor para Sessão de Estudo."""

    @staticmethod
    def to_domain(model: PoolSessionModel) -> FlashcardPoolSession:
        return FlashcardPoolSession(
            id=model.id,
            user_id=model.user_id,
            subject_id_filter=model.subject_id_filter,
            topic_id_filter=model.topic_id_filter,
            current_position=model.current_position,
            round_number=model.round_number,
            is_active=model.is_active,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: FlashcardPoolSession) -> PoolSessionModel:
        return PoolSessionModel(
            id=entity.id,
            user_id=entity.user_id,
            subject_id_filter=entity.subject_id_filter,
            topic_id_filter=entity.topic_id_filter,
            current_position=entity.current_position,
            round_number=entity.round_number,
            is_active=entity.is_active,
            updated_at=entity.updated_at,
        )
