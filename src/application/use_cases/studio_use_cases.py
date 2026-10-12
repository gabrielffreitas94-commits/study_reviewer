"""Casos de uso para o Studio Unificado de Criação de Conteúdo em Lote."""

from uuid import UUID

from src.application.dto.knowledge_dto import CreateKnowledgeSourceRequest
from src.application.dto.studio_dto import (
    BatchStudioPublishInputDTO,
    BatchStudioPublishResultDTO,
)
from src.application.ports.repositories import (
    IClockService,
    IQuestionProgressRepository,
    IQuestionRepository,
    ISubjectRepository,
    ITopicRepository,
    IUnitOfWork,
)
from src.application.use_cases.knowledge_use_cases import IngestKnowledgeSourceUseCase
from src.domain.entities import Question, Topic, UserQuestionProgress
from src.domain.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    ResourceOwnershipError,
)


class BatchStudioPublishUseCase:
    """Orquestra a criação atômica em lote de temas, bases de conhecimento e perguntas."""

    def __init__(
        self,
        subject_repo: ISubjectRepository,
        topic_repo: ITopicRepository,
        question_repo: IQuestionRepository,
        progress_repo: IQuestionProgressRepository,
        ingest_knowledge_use_case: IngestKnowledgeSourceUseCase,
        clock: IClockService,
        uow: IUnitOfWork | None = None,
    ) -> None:
        self._subject_repo = subject_repo
        self._topic_repo = topic_repo
        self._question_repo = question_repo
        self._progress_repo = progress_repo
        self._ingest_knowledge_use_case = ingest_knowledge_use_case
        self._clock = clock
        self._uow = uow

    async def execute(
        self, user_id: UUID, dto: BatchStudioPublishInputDTO
    ) -> BatchStudioPublishResultDTO:
        # 1. Validação de Titularidade da Matéria
        subject = self._subject_repo.get_by_id(dto.subject_id)
        if not subject:
            raise EntityNotFoundError("Matéria não encontrada.")
        if not subject.can_be_edited_by(user_id):
            raise ResourceOwnershipError(
                "Apenas o proprietário da matéria pode criar conteúdo nesta matéria."
            )

        today = self._clock.today()
        created_topics: list[Topic] = []
        created_source_ids: list[UUID] = []
        created_question_ids: list[UUID] = []

        try:
            # 2. Criação dos Novos Temas (On-the-fly)
            for raw_topic_name in dto.new_topics:
                clean_name = raw_topic_name.strip()
                if clean_name:
                    new_topic = Topic(subject_id=subject.id, name=clean_name)
                    self._topic_repo.save(new_topic)
                    created_topics.append(new_topic)

            existing_topics = self._topic_repo.list_by_subject(subject.id)
            existing_topic_ids = {t.id for t in existing_topics}

            if not created_topics and not existing_topics:
                raise DomainValidationError(
                    "A matéria selecionada não possui temas cadastrados. "
                    "Crie ao menos um tema no lote."
                )

            if not dto.questions:
                raise DomainValidationError("O lote deve conter pelo menos uma pergunta aberta.")

            # 3. Ingestão das Fontes de Conhecimento (com vínculos N:N)
            for source_dto in dto.new_sources:
                target_topic_ids: list[UUID] = []

                # Tópicos existentes por ID
                for t_id in source_dto.topic_ids:
                    if t_id in existing_topic_ids:
                        target_topic_ids.append(t_id)

                # Novos tópicos por índice da lista de novos temas criados no lote
                for idx in source_dto.topic_indices:
                    if 0 <= idx < len(created_topics):
                        target_topic_ids.append(created_topics[idx].id)

                # Fallback: se nenhum especificado, vincula aos novos ou ao primeiro existente
                if not target_topic_ids:
                    if created_topics:
                        target_topic_ids = [t.id for t in created_topics]
                    else:
                        target_topic_ids = [existing_topics[0].id]

                req = CreateKnowledgeSourceRequest(
                    title=source_dto.title,
                    content=source_dto.content,
                    content_type=source_dto.content_type,
                    topic_ids=list(dict.fromkeys(target_topic_ids)),
                )

                ingested = await self._ingest_knowledge_use_case.execute(
                    user_id=user_id,
                    topic_id=target_topic_ids[0],
                    request=req,
                )
                created_source_ids.append(ingested.id)

            # 4. Criação das Perguntas Abertas em Lote
            for q_dto in dto.questions:
                clean_prompt = q_dto.prompt.strip()
                clean_expected = q_dto.expected_answer.strip()

                if not clean_prompt or not clean_expected:
                    raise DomainValidationError(
                        "O enunciado e a resposta esperada da pergunta não podem ser vazios."
                    )

                target_topic_id: UUID
                if q_dto.topic_index is not None and 0 <= q_dto.topic_index < len(created_topics):
                    target_topic_id = created_topics[q_dto.topic_index].id
                elif q_dto.topic_id is not None and q_dto.topic_id in existing_topic_ids:
                    target_topic_id = q_dto.topic_id
                elif created_topics:
                    target_topic_id = created_topics[0].id
                else:
                    target_topic_id = existing_topics[0].id

                question = Question(
                    topic_id=target_topic_id,
                    prompt=clean_prompt,
                    expected_answer=clean_expected,
                    created_at=today,
                )
                self._question_repo.save(question)

                initial_progress = UserQuestionProgress(
                    user_id=user_id,
                    question_id=question.id,
                    current_level=0,
                    next_review_date=today,
                )
                self._progress_repo.save(initial_progress)
                created_question_ids.append(question.id)

            if self._uow is not None:
                self._uow.commit()

        except Exception:
            if self._uow is not None:
                self._uow.rollback()
            raise

        return BatchStudioPublishResultDTO(
            subject_id=subject.id,
            created_topics_count=len(created_topics),
            created_sources_count=len(created_source_ids),
            created_questions_count=len(created_question_ids),
            topic_ids=[t.id for t in created_topics],
            source_ids=created_source_ids,
            question_ids=created_question_ids,
        )
