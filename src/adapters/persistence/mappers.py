from datetime import UTC, datetime
from uuid import UUID

from src.adapters.persistence.models import (
    FlashcardModel,
    KnowledgeChunkModel,
    KnowledgeSourceModel,
    PoolSessionModel,
    QuestionModel,
    ReviewAuditLogModel,
    StudyEdgeModel,
    StudyMapModel,
    StudyNodeModel,
    SubjectModel,
    TokenLedgerModel,
    TokenTransactionModel,
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
    StudyEdge,
    StudyMap,
    StudyNode,
    Subject,
    TokenLedger,
    TokenTransaction,
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
    """Conversor para Pergunta Aberta (Sprint 03 / N:N)."""

    @staticmethod
    def to_domain(model: QuestionModel) -> Question:
        topic_ids = tuple(t.id for t in model.topics) if getattr(model, "topics", None) else ()
        tid = getattr(model, "topic_id", None)
        if not topic_ids and tid is not None:
            topic_ids = (tid,)
        node_id = getattr(model, "node_id", None)
        if not topic_ids and node_id is not None:
            topic_ids = (node_id,)
        return Question(
            id=model.id,
            topic_ids=topic_ids,
            node_id=node_id,
            prompt=str(model.prompt),
            expected_answer=str(model.expected_answer),
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Question) -> QuestionModel:
        topic_id = None
        if entity.topic_ids:
            real_topics = [tid for tid in entity.topic_ids if tid != entity.node_id]
            if real_topics:
                topic_id = real_topics[0]
        return QuestionModel(
            id=entity.id,
            topic_id=topic_id,
            node_id=entity.node_id,
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
    """Conversor para Fonte de Conhecimento (Sprint 07/N:N)."""

    @staticmethod
    def to_domain(model: KnowledgeSourceModel) -> KnowledgeSource:
        topic_ids = tuple(t.id for t in model.topics) if getattr(model, "topics", None) else ()
        tid = getattr(model, "topic_id", None)
        if not topic_ids and tid is not None:
            topic_ids = (tid,)
        node_id = getattr(model, "node_id", None)
        if not topic_ids and node_id is not None:
            topic_ids = (node_id,)
        return KnowledgeSource(
            id=model.id,
            title=model.title,
            topic_ids=topic_ids,
            node_id=node_id,
            raw_text=getattr(model, "raw_text", "") or "",
            content_type=model.content_type,
            total_chunks=model.total_chunks,
            char_count=model.char_count,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: KnowledgeSource) -> KnowledgeSourceModel:
        topic_id = None
        if entity.topic_ids:
            real_topics = [tid for tid in entity.topic_ids if tid != entity.node_id]
            if real_topics:
                topic_id = real_topics[0]
        return KnowledgeSourceModel(
            id=entity.id,
            topic_id=topic_id,
            node_id=entity.node_id,
            title=entity.title,
            content_type=entity.content_type,
            total_chunks=entity.total_chunks,
            char_count=entity.char_count,
            raw_text=entity.raw_text,
            created_at=entity.created_at,
        )


class KnowledgeChunkMapper:
    """Conversor para Fragmento de Conhecimento Vetorizado (Sprint 07)."""

    @staticmethod
    def to_domain(model: KnowledgeChunkModel) -> KnowledgeChunk:
        return KnowledgeChunk(
            id=model.id,
            source_id=model.source_id,
            topic_id=model.topic_id or model.source_id,
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


class TokenLedgerMapper:
    """Conversor para Saldo/Ledger de Tokens (Sprint 08)."""

    @staticmethod
    def to_domain(model: TokenLedgerModel) -> TokenLedger:
        return TokenLedger(
            user_id=model.user_id,
            balance=model.balance,
            held_balance=model.held_balance,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: TokenLedger) -> TokenLedgerModel:
        return TokenLedgerModel(
            user_id=entity.user_id,
            balance=entity.balance,
            held_balance=entity.held_balance,
            updated_at=entity.updated_at,
        )


class TokenTransactionMapper:
    """Conversor para Transação de Tokens (Sprint 08)."""

    @staticmethod
    def to_domain(model: TokenTransactionModel) -> TokenTransaction:
        return TokenTransaction(
            id=model.id,
            user_id=model.user_id,
            transaction_type=model.transaction_type,
            amount=model.amount,
            reference_id=model.reference_id,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: TokenTransaction) -> TokenTransactionModel:
        return TokenTransactionModel(
            id=entity.id,
            user_id=entity.user_id,
            transaction_type=entity.transaction_type,
            amount=entity.amount,
            reference_id=entity.reference_id,
            created_at=entity.created_at,
        )


class StudyMapMapper:
    """Conversor para Mapa de Estudos RPG."""

    @staticmethod
    def to_domain(model: StudyMapModel) -> StudyMap:
        return StudyMap(
            id=model.id,
            owner_id=model.owner_id,
            title=model.title,
            description=model.description,
            is_public=model.is_public,
            parent_node_id=model.parent_node_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: StudyMap) -> StudyMapModel:
        return StudyMapModel(
            id=entity.id,
            owner_id=entity.owner_id,
            title=entity.title,
            description=entity.description,
            is_public=entity.is_public,
            parent_node_id=entity.parent_node_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class StudyNodeMapper:
    """Conversor para Nó da Árvore de Conhecimento."""

    @staticmethod
    def to_domain(model: StudyNodeModel) -> StudyNode:
        return StudyNode(
            id=model.id,
            map_id=model.map_id,
            title=model.title,
            description=model.description,
            theory_content=getattr(model, "theory_content", "") or "",
            pos_x=model.pos_x,
            pos_y=model.pos_y,
            icon=model.icon,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: StudyNode) -> StudyNodeModel:
        return StudyNodeModel(
            id=entity.id,
            map_id=entity.map_id,
            title=entity.title,
            description=entity.description,
            theory_content=entity.theory_content,
            pos_x=entity.pos_x,
            pos_y=entity.pos_y,
            icon=entity.icon,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class StudyEdgeMapper:
    """Conversor para Aresta de Pré-requisito."""

    @staticmethod
    def to_domain(model: StudyEdgeModel) -> StudyEdge:
        return StudyEdge(
            id=model.id,
            map_id=model.map_id,
            source_node_id=model.source_node_id,
            target_node_id=model.target_node_id,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: StudyEdge) -> StudyEdgeModel:
        return StudyEdgeModel(
            id=entity.id,
            map_id=entity.map_id,
            source_node_id=entity.source_node_id,
            target_node_id=entity.target_node_id,
            created_at=entity.created_at,
        )
