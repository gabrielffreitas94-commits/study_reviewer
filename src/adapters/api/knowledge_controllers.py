"""Controladores REST para Materiais Didáticos Locais."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
)
from src.application.dto.knowledge_dto import (
    CreateKnowledgeSourceRequest,
    LinkKnowledgeSourceRequest,
)
from src.application.use_cases.knowledge_use_cases import (
    DeleteKnowledgeSourceUseCase,
    GetTopicKnowledgeSourcesUseCase,
    IngestKnowledgeSourceUseCase,
    LinkKnowledgeSourceToTopicsUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    EmptyKnowledgeContentError,
    EntityNotFoundError,
    KnowledgeSourceNotFoundError,
    ResourceOwnershipError,
)
from src.domain.services import DocumentTextExtractorService
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import get_current_user

api_knowledge_router = APIRouter(prefix="/api/v1", tags=["Study Materials"])


class IngestSourceRequest(BaseModel):
    """Payload de entrada para ingestão de material didático."""

    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=20, max_length=200000)
    content_type: str = Field(default="TEXT", max_length=50)
    topic_ids: list[UUID] = Field(default_factory=list)


class LinkTopicsRequest(BaseModel):
    """Payload para associar temas a uma fonte de conhecimento."""

    topic_ids: list[UUID] = Field(..., min_length=1)


@api_knowledge_router.post(
    "/topics/{topic_id}/knowledge",
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar material didático no tema",
)
async def ingest_knowledge_source(
    topic_id: UUID,
    payload: IngestSourceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    source_repo = SqlAlchemyKnowledgeSourceRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)

    use_case = IngestKnowledgeSourceUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    req = CreateKnowledgeSourceRequest(
        title=payload.title,
        content=payload.content,
        content_type=payload.content_type,
        topic_ids=payload.topic_ids or [topic_id],
    )

    try:
        res = await use_case.execute(user_id=user.id, topic_id=topic_id, request=req)
        db.commit()
        return {
            "id": str(res.id),
            "topic_id": str(res.topic_id),
            "title": res.title,
            "content_type": res.content_type,
            "total_chunks": res.total_chunks,
            "char_count": res.char_count,
            "created_at": res.created_at,
            "topic_ids": [str(tid) for tid in res.topic_ids],
        }
    except EntityNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ResourceOwnershipError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except (EmptyKnowledgeContentError, DomainValidationError) as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@api_knowledge_router.put(
    "/knowledge/{source_id}/topics",
    status_code=status.HTTP_200_OK,
    summary="Associar/Atualizar temas de uma fonte de conhecimento (N:N)",
)
async def link_knowledge_source_topics(
    source_id: UUID,
    payload: LinkTopicsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    source_repo = SqlAlchemyKnowledgeSourceRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)

    use_case = LinkKnowledgeSourceToTopicsUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    req = LinkKnowledgeSourceRequest(
        source_id=source_id,
        topic_ids=payload.topic_ids,
    )

    try:
        res = await use_case.execute(user_id=user.id, request=req)
        db.commit()
        return {
            "id": str(res.id),
            "topic_id": str(res.topic_id),
            "title": res.title,
            "content_type": res.content_type,
            "total_chunks": res.total_chunks,
            "char_count": res.char_count,
            "created_at": res.created_at,
            "topic_ids": [str(tid) for tid in res.topic_ids],
        }
    except (KnowledgeSourceNotFoundError, EntityNotFoundError) as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ResourceOwnershipError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except DomainValidationError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@api_knowledge_router.post(
    "/knowledge/extract-file",
    status_code=status.HTTP_200_OK,
    summary="Extrair texto de arquivo PDF, DOCX ou TXT para materiais didáticos",
)
async def extract_file_text(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    content_bytes = await file.read()
    if len(content_bytes) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Arquivo excede o limite máximo de 15 MB.",
        )

    try:
        extracted = DocumentTextExtractorService.extract_text(
            file_bytes=content_bytes,
            filename=file.filename or "document.txt",
            mime_type=file.content_type,
        )
        return {
            "filename": file.filename or "document.txt",
            "extracted_text": extracted,
            "text_preview": extracted[:2000],
            "char_count": len(extracted),
            "chunk_estimate": max(1, len(extracted) // 600),
        }
    except DomainValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@api_knowledge_router.get(
    "/topics/{topic_id}/knowledge",
    status_code=status.HTTP_200_OK,
    summary="Listar materiais didáticos de um tema",
)
async def list_topic_knowledge_sources(
    topic_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    source_repo = SqlAlchemyKnowledgeSourceRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)

    use_case = GetTopicKnowledgeSourcesUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    try:
        sources = await use_case.execute(user_id=user.id, topic_id=topic_id)
        return [
            {
                "id": str(s.id),
                "topic_id": str(s.topic_id),
                "title": s.title,
                "content_type": s.content_type,
                "total_chunks": s.total_chunks,
                "char_count": s.char_count,
                "created_at": s.created_at,
                "topic_ids": [str(tid) for tid in s.topic_ids],
            }
            for s in sources
        ]
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ResourceOwnershipError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@api_knowledge_router.delete(
    "/knowledge/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover material didático",
)
async def delete_knowledge_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    source_repo = SqlAlchemyKnowledgeSourceRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)

    use_case = DeleteKnowledgeSourceUseCase(
        source_repo=source_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    try:
        await use_case.execute(user_id=user.id, source_id=source_id)
        db.commit()
    except KnowledgeSourceNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EntityNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ResourceOwnershipError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
