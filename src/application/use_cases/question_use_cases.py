import logging
from uuid import UUID

from src.application.dto.question_dto import (
    CreateQuestionDTO,
    DueQuestionItemDTO,
    QuestionDTO,
    ReviewQuestionInputDTO,
    ReviewQuestionResultDTO,
    UpdateQuestionDTO,
)
from src.application.ports.repositories import (
    IClockService,
    IQuestionProgressRepository,
    IQuestionRepository,
    IReviewAuditRepository,
    ISubjectRepository,
    ITopicRepository,
    IUnitOfWork,
)
from src.domain.entities import Question, ReviewAuditLog, UserQuestionProgress
from src.domain.exceptions import (
    EntityNotFoundError,
    QuestionNotDueError,
    QuestionNotFoundError,
    ResourceOwnershipError,
)
from src.domain.services import SpacingPolicyService

logger = logging.getLogger("study_reviewer")


class CreateQuestionUseCase:
    """Caso de uso para criação de uma nova Pergunta Aberta vinculada a um Tema."""

    def __init__(
        self,
        question_repo: IQuestionRepository,
        progress_repo: IQuestionProgressRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
        clock: IClockService,
        uow: IUnitOfWork | None = None,
    ) -> None:
        self._question_repo = question_repo
        self._progress_repo = progress_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo
        self._clock = clock
        self._uow = uow

    def execute(self, dto: CreateQuestionDTO, user_id: UUID) -> QuestionDTO:
        topic = self._topic_repo.get_by_id(dto.topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_edited_by(user_id):
            raise ResourceOwnershipError("Apenas o proprietário da matéria pode criar perguntas.")

        question = Question(
            topic_id=dto.topic_id,
            prompt=dto.prompt,
            expected_answer=dto.expected_answer,
            created_at=self._clock.today(),
        )

        initial_progress = UserQuestionProgress(
            user_id=user_id,
            question_id=question.id,
            current_level=0,
            next_review_date=self._clock.today(),
        )

        try:
            self._question_repo.save(question)
            self._progress_repo.save(initial_progress)

            if self._uow is not None:
                self._uow.commit()
        except Exception:
            if self._uow is not None:
                self._uow.rollback()
            raise

        return QuestionDTO(
            id=question.id,
            topic_id=question.topic_id,
            prompt=question.prompt,
            expected_answer=question.expected_answer,
            created_at=question.created_at,
        )


class UpdateQuestionUseCase:
    """Caso de uso para atualização de enunciado ou gabarito pelo proprietário."""

    def __init__(
        self,
        question_repo: IQuestionRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._question_repo = question_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    def execute(self, dto: UpdateQuestionDTO, user_id: UUID) -> QuestionDTO:
        question = self._question_repo.get_by_id(dto.question_id)
        if not question:
            raise QuestionNotFoundError("Pergunta não encontrada.")

        topic = self._topic_repo.get_by_id(question.topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_edited_by(user_id):
            raise ResourceOwnershipError("Apenas o proprietário da matéria pode editar a pergunta.")

        question.prompt = dto.prompt
        question.expected_answer = dto.expected_answer
        question.__post_init__()

        self._question_repo.save(question)

        return QuestionDTO(
            id=question.id,
            topic_id=question.topic_id,
            prompt=question.prompt,
            expected_answer=question.expected_answer,
            created_at=question.created_at,
        )


class DeleteQuestionUseCase:
    """Caso de uso para exclusão de pergunta aberta pelo proprietário."""

    def __init__(
        self,
        question_repo: IQuestionRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._question_repo = question_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    def execute(self, question_id: UUID, user_id: UUID) -> None:
        question = self._question_repo.get_by_id(question_id)
        if not question:
            raise QuestionNotFoundError("Pergunta não encontrada.")

        topic = self._topic_repo.get_by_id(question.topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_edited_by(user_id):
            raise ResourceOwnershipError(
                "Apenas o proprietário da matéria pode excluir a pergunta."
            )

        self._question_repo.delete(question_id)


class ListQuestionsByTopicUseCase:
    """Caso de uso para listar perguntas de um tema (proprietário ou matéria pública)."""

    def __init__(
        self,
        question_repo: IQuestionRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._question_repo = question_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    def execute(self, topic_id: UUID, user_id: UUID) -> list[QuestionDTO]:
        topic = self._topic_repo.get_by_id(topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_studied_by(user_id):
            raise ResourceOwnershipError("Acesso negado às perguntas desta matéria.")

        questions = self._question_repo.list_by_topic(topic_id)
        return [
            QuestionDTO(
                id=q.id,
                topic_id=q.topic_id,
                prompt=q.prompt,
                expected_answer=q.expected_answer,
                created_at=q.created_at,
            )
            for q in questions
        ]


class GetQuestionByIdUseCase:
    """Caso de uso para buscar uma pergunta específica por ID validando autorização."""

    def __init__(
        self,
        question_repo: IQuestionRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._question_repo = question_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    def execute(self, question_id: UUID, user_id: UUID) -> QuestionDTO:
        question = self._question_repo.get_by_id(question_id)
        if not question:
            raise QuestionNotFoundError("Pergunta não encontrada.")

        topic = self._topic_repo.get_by_id(question.topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_studied_by(user_id):
            raise ResourceOwnershipError("Acesso negado a esta pergunta.")

        return QuestionDTO(
            id=question.id,
            topic_id=question.topic_id,
            prompt=question.prompt,
            expected_answer=question.expected_answer,
            created_at=question.created_at,
        )


class GetDueQuestionsUseCase:
    """Caso de uso de consulta da fila de perguntas vencidas (CQS estrito)."""

    def __init__(
        self,
        progress_repo: IQuestionProgressRepository,
        question_repo: IQuestionRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
        clock: IClockService,
    ) -> None:
        self._progress_repo = progress_repo
        self._question_repo = question_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo
        self._clock = clock

    def execute(
        self,
        user_id: UUID,
        subject_id: UUID | None = None,
        topic_id: UUID | None = None,
        limit: int = 50,
    ) -> list[DueQuestionItemDTO]:
        if subject_id is not None:
            subject = self._subject_repo.get_by_id(subject_id)
            if not subject:
                raise EntityNotFoundError("Matéria não encontrada.")
            if not subject.can_be_studied_by(user_id):
                raise ResourceOwnershipError("Acesso negado a esta matéria.")

            # Inicializa em lote com ON CONFLICT DO NOTHING se for matéria sob demanda
            topics = self._topic_repo.list_by_subject(subject_id)
            all_q_ids: list[UUID] = []
            for t in topics:
                all_q_ids.extend([q.id for q in self._question_repo.list_by_topic(t.id)])
            self._progress_repo.initialize_progress_for_questions(
                user_id, all_q_ids, self._clock.today()
            )

        elif topic_id is not None:
            topic = self._topic_repo.get_by_id(topic_id)
            if not topic:
                raise EntityNotFoundError("Tema não encontrado.")
            subject = self._subject_repo.get_by_id(topic.subject_id)
            if not subject or not subject.can_be_studied_by(user_id):
                raise ResourceOwnershipError("Acesso negado a este tema.")

            q_ids = [q.id for q in self._question_repo.list_by_topic(topic_id)]
            self._progress_repo.initialize_progress_for_questions(
                user_id, q_ids, self._clock.today()
            )

        return self._progress_repo.get_due_questions(
            user_id=user_id,
            reference_date=self._clock.today(),
            subject_id=subject_id,
            topic_id=topic_id,
            limit=limit,
        )


class ReviewQuestionUseCase:
    """Caso de uso para submissão de nota e recalculo de repetição espaçada."""

    def __init__(
        self,
        progress_repo: IQuestionProgressRepository,
        question_repo: IQuestionRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
        clock: IClockService,
        audit_repo: IReviewAuditRepository | None = None,
        uow: IUnitOfWork | None = None,
    ) -> None:
        self._progress_repo = progress_repo
        self._question_repo = question_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo
        self._clock = clock
        self._audit_repo = audit_repo
        self._uow = uow

    def execute(self, dto: ReviewQuestionInputDTO, user_id: UUID) -> ReviewQuestionResultDTO:
        question = self._question_repo.get_by_id(dto.question_id)
        if not question:
            raise QuestionNotFoundError("Pergunta não encontrada.")

        topic = self._topic_repo.get_by_id(question.topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_studied_by(user_id):
            raise ResourceOwnershipError("Acesso negado para estudar esta pergunta.")

        progress = self._progress_repo.get_by_user_and_question(user_id, dto.question_id)
        if progress is None:
            # Provisionamento JIT se for o primeiro estudo em matéria pública
            progress = UserQuestionProgress(
                user_id=user_id,
                question_id=dto.question_id,
                current_level=0,
                next_review_date=self._clock.today(),
            )

        today = self._clock.today()
        is_confirming_ai_review = False
        previous_level = progress.current_level

        if self._audit_repo is not None:
            recent_logs = self._audit_repo.list_by_user(user_id=user_id, limit=20)
            today_logs = [
                log
                for log in recent_logs
                if log.question_id == dto.question_id and log.review_date == today
            ]
            if today_logs:
                latest_log = today_logs[0]
                if latest_log.evaluation_mode != "MANUAL":
                    is_confirming_ai_review = True
                    previous_level = today_logs[-1].level_before

        if progress.next_review_date > today and not is_confirming_ai_review:
            raise QuestionNotDueError(
                f"A pergunta '{dto.question_id}' não está vencida para revisão "
                f"(vencimento: {progress.next_review_date})."
            )

        new_level, next_date = SpacingPolicyService.calculate_next_schedule(
            current_level=previous_level,
            score=dto.score,
            review_date=today,
        )

        now = self._clock.now()
        progress.apply_review(
            new_level=new_level,
            next_date=next_date,
            reviewed_at=now,
        )

        try:
            self._progress_repo.save(progress)
            if self._audit_repo is not None:
                audit_log = ReviewAuditLog(
                    user_id=user_id,
                    question_id=dto.question_id,
                    subject_id=subject.id,
                    topic_id=topic.id,
                    historical_subject_name=subject.name,
                    historical_topic_name=topic.name,
                    review_date=today,
                    score=dto.score,
                    level_before=previous_level,
                    level_after=new_level,
                    evaluation_mode="MANUAL",
                    logged_at=now,
                )
                self._audit_repo.save(audit_log)

            if self._uow is not None:
                self._uow.commit()
        except Exception:
            if self._uow is not None:
                self._uow.rollback()
            raise

        is_promoted = new_level > previous_level
        is_regressed = new_level < previous_level
        interval_days = SpacingPolicyService.INTERVALS[min(new_level, 6)]

        logger.info(
            "srs_question_reviewed: user=%s question=%s score=%s prev_level=%s new_level=%s "
            "interval_days=%s is_promoted=%s is_regressed=%s",
            user_id,
            dto.question_id,
            dto.score,
            previous_level,
            new_level,
            interval_days,
            is_promoted,
            is_regressed,
            extra={
                "event": "srs_question_reviewed",
                "user_id": str(user_id),
                "question_id": str(dto.question_id),
                "score": dto.score,
                "previous_level": previous_level,
                "new_level": new_level,
                "interval_days": interval_days,
                "is_promoted": is_promoted,
                "is_regressed": is_regressed,
            },
        )

        return ReviewQuestionResultDTO(
            question_id=dto.question_id,
            previous_level=previous_level,
            new_level=new_level,
            next_review_date=next_date,
            interval_days=interval_days,
            is_promoted=is_promoted,
            is_regressed=is_regressed,
        )
