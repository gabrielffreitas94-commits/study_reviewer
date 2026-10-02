"""Mappers bidirecionais entre entidades puras de domínio e modelos ORM (Camada 3 - Adaptadores)."""

from src.adapters.persistence.models import (
    FlashcardModel,
    PoolSessionModel,
    SubjectModel,
    TopicModel,
)
from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic


class SubjectMapper:
    """Conversor para Matéria."""

    @staticmethod
    def to_domain(model: SubjectModel) -> Subject:
        return Subject(
            id=model.id,
            name=model.name,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Subject) -> SubjectModel:
        return SubjectModel(
            id=entity.id,
            name=entity.name,
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
    """Conversor para Flashcard."""

    @staticmethod
    def to_domain(model: FlashcardModel) -> Flashcard:
        return Flashcard(
            id=model.id,
            topic_id=model.topic_id,
            front=model.front,
            back=model.back,
            position=model.position,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Flashcard) -> FlashcardModel:
        return FlashcardModel(
            id=entity.id,
            topic_id=entity.topic_id,
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
            subject_id_filter=entity.subject_id_filter,
            topic_id_filter=entity.topic_id_filter,
            current_position=entity.current_position,
            round_number=entity.round_number,
            is_active=entity.is_active,
            updated_at=entity.updated_at,
        )
