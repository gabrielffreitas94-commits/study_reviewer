from datetime import UTC, datetime
from uuid import UUID

from src.adapters.persistence.models import (
    FlashcardModel,
    KnowledgeChunkModel,
    KnowledgeSourceModel,
    PoolSessionModel,
    QuestionModel,
    ReviewAuditLogModel,
    SubjectModel,
    TopicModel,
    UserModel,
    UserQuestionProgressModel,
)
from src.domain.entities import (
    Flashcard,
    FlashcardPoolSession,
    KnowledgeChunk,
    KnowledgeSource,
    Question,
    ReviewAuditLog,
    Subject,
    Topic,
    User,
    UserQuestionProgress,
)


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
        queue = [UUID(str(uid)) for uid in model.card_queue] if model.card_queue else []
        return FlashcardPoolSession(
            id=model.id,
            user_id=model.user_id,
            subject_id_filter=model.subject_id_filter,
            topic_id_filter=model.topic_id_filter,
            current_position=model.current_position,
            round_number=model.round_number,
            is_active=model.is_active,
            updated_at=model.updated_at,
            current_index=model.current_index,
            card_queue=queue,
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
            current_index=entity.current_index,
            card_queue=[str(cid) for cid in entity.card_queue],
        )


class QuestionMapper:
    """Conversor para Pergunta Aberta (Sprint 03)."""

    @staticmethod
    def to_domain(model: QuestionModel) -> Question:
        return Question(
            id=model.id,
            topic_id=model.topic_id,
            prompt=str(model.prompt),
            expected_answer=str(model.expected_answer),
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Question) -> QuestionModel:
        return QuestionModel(
            id=entity.id,
            topic_id=entity.topic_id,
            prompt=entity.prompt,
            expected_answer=entity.expected_answer,
            created_at=entity.created_at,
        )


class QuestionProgressMapper:
    """Conversor para Progresso de Pergunta Aberta (Sprint 03)."""

    @staticmethod
    def to_domain(model: UserQuestionProgressModel) -> UserQuestionProgress:
        return UserQuestionProgress(
            id=model.id,
            user_id=model.user_id,
            question_id=model.question_id,
            current_level=model.current_level,
            next_review_date=model.next_review_date,
            last_reviewed_at=model.last_reviewed_at,
        )

    @staticmethod
    def to_model(entity: UserQuestionProgress) -> UserQuestionProgressModel:
        return UserQuestionProgressModel(
            id=entity.id,
            user_id=entity.user_id,
            question_id=entity.question_id,
            current_level=entity.current_level,
            next_review_date=entity.next_review_date,
            last_reviewed_at=entity.last_reviewed_at,
        )


class ReviewAuditLogMapper:
    """Conversor para Trilha de Auditoria Histórica (Sprint 04)."""

    @staticmethod
    def to_domain(model: ReviewAuditLogModel) -> ReviewAuditLog:
        return ReviewAuditLog(
            id=model.id,
            user_id=model.user_id,
            question_id=model.question_id,
            subject_id=model.subject_id,
            topic_id=model.topic_id,
            historical_subject_name=model.historical_subject_name,
            historical_topic_name=model.historical_topic_name,
            review_date=model.review_date,
            score=model.score,
            level_before=model.level_before,
            level_after=model.level_after,
            evaluation_mode=model.evaluation_mode,
            logged_at=model.logged_at,
        )

    @staticmethod
    def to_model(entity: ReviewAuditLog) -> ReviewAuditLogModel:
        return ReviewAuditLogModel(
            id=entity.id,
            user_id=entity.user_id,
            question_id=entity.question_id,
            subject_id=entity.subject_id,
            topic_id=entity.topic_id,
            historical_subject_name=entity.historical_subject_name,
            historical_topic_name=entity.historical_topic_name,
            review_date=entity.review_date,
            score=entity.score,
            level_before=entity.level_before,
            level_after=entity.level_after,
            evaluation_mode=entity.evaluation_mode,
            logged_at=entity.logged_at or datetime.now(UTC),
        )


class KnowledgeSourceMapper:
    """Conversor para Fonte de Conhecimento (Sprint 07)."""

    @staticmethod
    def to_domain(model: KnowledgeSourceModel) -> KnowledgeSource:
        return KnowledgeSource(
            id=model.id,
            topic_id=model.topic_id,
            title=model.title,
            content_type=model.content_type,
            total_chunks=model.total_chunks,
            char_count=model.char_count,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: KnowledgeSource) -> KnowledgeSourceModel:
        return KnowledgeSourceModel(
            id=entity.id,
            topic_id=entity.topic_id,
            title=entity.title,
            content_type=entity.content_type,
            total_chunks=entity.total_chunks,
            char_count=entity.char_count,
            created_at=entity.created_at,
        )


class KnowledgeChunkMapper:
    """Conversor para Fragmento de Conhecimento Vetorizado (Sprint 07)."""

    @staticmethod
    def to_domain(model: KnowledgeChunkModel) -> KnowledgeChunk:
        return KnowledgeChunk(
            id=model.id,
            source_id=model.source_id,
            topic_id=model.topic_id,
            chunk_index=model.chunk_index,
            content=model.content,
            embedding=tuple(model.embedding),
            token_estimate=model.token_estimate,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: KnowledgeChunk) -> KnowledgeChunkModel:
        return KnowledgeChunkModel(
            id=entity.id,
            source_id=entity.source_id,
            topic_id=entity.topic_id,
            chunk_index=entity.chunk_index,
            content=entity.content,
            embedding=list(entity.embedding),
            token_estimate=entity.token_estimate,
            created_at=entity.created_at,
        )
