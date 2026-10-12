"""Controladores REST para o Studio Unificado de Criação em Lote."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.ai.gemini_adapters import GeminiEmbeddingAdapter
from src.adapters.persistence.repositories import (
    SqlAlchemyKnowledgeChunkRepository,
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
    SqlAlchemyUnitOfWork,
)
from src.application.dto.studio_dto import (
    BatchStudioPublishInputDTO,
    StudioNewQuestionDTO,
    StudioNewSourceDTO,
)
from src.application.use_cases.knowledge_use_cases import IngestKnowledgeSourceUseCase
from src.application.use_cases.studio_use_cases import BatchStudioPublishUseCase
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    EmptyKnowledgeContentError,
    EntityNotFoundError,
    ResourceOwnershipError,
)
from src.infrastructure.clock import system_clock
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import get_current_user
from src.infrastructure.security.sanitization import MarkdownSanitizerService

api_studio_router = APIRouter(prefix="/api/v1/studio", tags=["Studio Batch Publishing"])


class StudioNewSourcePayload(BaseModel):
    """Payload de uma nova fonte no lote."""

    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=20, max_length=200000)
    topic_ids: list[UUID] = Field(default_factory=list)
    topic_indices: list[int] = Field(default_factory=list)
    content_type: str = Field(default="TEXT", max_length=50)


class StudioNewQuestionPayload(BaseModel):
    """Payload de uma nova pergunta no lote."""

    prompt: str = Field(..., min_length=1, max_length=10000)
    expected_answer: str = Field(..., min_length=1, max_length=10000)
    topic_id: UUID | None = None
    topic_index: int | None = None


class BatchStudioPublishPayload(BaseModel):
    """Payload completo de publicação em lote no Studio."""

    subject_id: UUID
    new_topics: list[str] = Field(default_factory=list)
    new_sources: list[StudioNewSourcePayload] = Field(default_factory=list)
    questions: list[StudioNewQuestionPayload] = Field(default_factory=list)


@api_studio_router.post(
    "/batch-publish",
    status_code=status.HTTP_201_CREATED,
    summary="Publicar atomicamente em lote novos temas, bases de conhecimento e perguntas",
)
async def batch_studio_publish(
    payload: BatchStudioPublishPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    source_repo = SqlAlchemyKnowledgeSourceRepository(db)
    chunk_repo = SqlAlchemyKnowledgeChunkRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)
    question_repo = SqlAlchemyQuestionRepository(db)
    progress_repo = SqlAlchemyQuestionProgressRepository(db)
    uow = SqlAlchemyUnitOfWork(db)

    embedding_service = GeminiEmbeddingAdapter(api_key=getattr(settings, "GEMINI_API_KEY", None))
    ingest_use_case = IngestKnowledgeSourceUseCase(
        source_repo=source_repo,
        chunk_repo=chunk_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
        embedding_service=embedding_service,
    )

    batch_use_case = BatchStudioPublishUseCase(
        subject_repo=subject_repo,
        topic_repo=topic_repo,
        question_repo=question_repo,
        progress_repo=progress_repo,
        ingest_knowledge_use_case=ingest_use_case,
        clock=system_clock,
        uow=uow,
    )

    input_dto = BatchStudioPublishInputDTO(
        subject_id=payload.subject_id,
        new_topics=payload.new_topics,
        new_sources=[
            StudioNewSourceDTO(
                title=s.title,
                content=s.content,
                topic_ids=s.topic_ids,
                topic_indices=s.topic_indices,
                content_type=s.content_type,
            )
            for s in payload.new_sources
        ],
        questions=[
            StudioNewQuestionDTO(
                prompt=MarkdownSanitizerService.sanitize(q.prompt),
                expected_answer=MarkdownSanitizerService.sanitize(q.expected_answer),
                topic_id=q.topic_id,
                topic_index=q.topic_index,
            )
            for q in payload.questions
        ],
    )

    try:
        res = await batch_use_case.execute(user_id=user.id, dto=input_dto)
        return {
            "subject_id": str(res.subject_id),
            "created_topics_count": res.created_topics_count,
            "created_sources_count": res.created_sources_count,
            "created_questions_count": res.created_questions_count,
            "topic_ids": [str(tid) for tid in res.topic_ids],
            "source_ids": [str(sid) for sid in res.source_ids],
            "question_ids": [str(qid) for qid in res.question_ids],
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ResourceOwnershipError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (DomainValidationError, EmptyKnowledgeContentError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
