"""Controladores Web para Gestão da Base de Conhecimento e Upload de Documentos."""

from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.adapters.ai.gemini_adapters import GeminiEmbeddingAdapter
from src.adapters.persistence.repositories import (
    SqlAlchemyKnowledgeChunkRepository,
    SqlAlchemyKnowledgeSourceRepository,
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyTopicRepository,
)
from src.application.dto.knowledge_dto import CreateKnowledgeSourceRequest
from src.application.use_cases.knowledge_use_cases import (
    DeleteKnowledgeSourceUseCase,
    IngestKnowledgeSourceUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import (
    DomainValidationError,
    EmptyKnowledgeContentError,
    EntityNotFoundError,
    ResourceOwnershipError,
)
from src.domain.services import DocumentTextExtractorService
from src.infrastructure.clock import system_clock
from src.infrastructure.config import settings
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import get_current_user

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

web_knowledge_router = APIRouter()


@web_knowledge_router.get("/knowledge/manage", response_model=None)
def manage_knowledge_view(
    request: Request,
    subject_id: str | None = Query(None),
    error: str | None = Query(None),
    success: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Renderiza a tela de gestão da base de conhecimento."""
    subj_repo = SqlAlchemySubjectRepository(db)
    top_repo = SqlAlchemyTopicRepository(db)
    source_repo = SqlAlchemyKnowledgeSourceRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)

    subjects = subj_repo.list_by_owner(current_user.id)
    total_due = prog_repo.count_due_questions(current_user.id, system_clock.today())

    topics_by_subject: dict[str, list[Any]] = {}
    all_sources_dict: dict[str, Any] = {}

    for s in subjects:
        s_topics = top_repo.list_by_subject(s.id)
        topics_by_subject[str(s.id)] = s_topics
        for t in s_topics:
            t_sources = source_repo.list_by_topic(t.id)
            for src in t_sources:
                all_sources_dict[str(src.id)] = src

    all_sources = list(all_sources_dict.values())
    all_sources.sort(key=lambda item: item.created_at, reverse=True)

    return templates.TemplateResponse(
        request=request,
        name="knowledge/manage.html",
        context={
            "current_user": current_user,
            "subjects": subjects,
            "topics_by_subject": topics_by_subject,
            "sources": all_sources,
            "pending_questions_count": total_due,
            "error": error,
            "success": success,
        },
    )


@web_knowledge_router.post("/knowledge/manage", response_model=None)
async def create_knowledge_source_web(
    request: Request,
    title: Annotated[str, Form()],
    content_text: Annotated[str, Form()] = "",
    topic_ids: Annotated[list[str], Form()] = [],
    document_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Processa a criação de fonte de conhecimento via formulário web (texto ou upload)."""
    raw_content = content_text.strip() if content_text else ""

    if document_file and document_file.filename:
        try:
            file_bytes = await document_file.read()
            if len(file_bytes) > 15 * 1024 * 1024:
                return RedirectResponse(
                    url="/knowledge/manage?error=Arquivo+excede+o+limite+máximo+de+15MB.",
                    status_code=status.HTTP_303_SEE_OTHER,
                )
            extracted = DocumentTextExtractorService.extract_text(
                file_bytes=file_bytes,
                filename=document_file.filename,
                mime_type=document_file.content_type,
            )
            raw_content = extracted.strip()
        except DomainValidationError as err:
            return RedirectResponse(
                url=f"/knowledge/manage?error={err}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    parsed_topic_ids: list[UUID] = []
    for tid_str in topic_ids:
        try:
            parsed_topic_ids.append(UUID(tid_str))
        except (ValueError, TypeError):
            continue

    if not parsed_topic_ids:
        return RedirectResponse(
            url="/knowledge/manage?error=Selecione+ao+menos+1+tema+para+vincular+o+material.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    source_repo = SqlAlchemyKnowledgeSourceRepository(db)
    chunk_repo = SqlAlchemyKnowledgeChunkRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)
    embedding_service = GeminiEmbeddingAdapter(api_key=getattr(settings, "GEMINI_API_KEY", None))

    use_case = IngestKnowledgeSourceUseCase(
        source_repo=source_repo,
        chunk_repo=chunk_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
        embedding_service=embedding_service,
    )

    req = CreateKnowledgeSourceRequest(
        title=title,
        content=raw_content,
        content_type="FILE" if (document_file and document_file.filename) else "TEXT",
        topic_ids=parsed_topic_ids,
    )

    try:
        await use_case.execute(user_id=current_user.id, topic_id=parsed_topic_ids[0], request=req)
        db.commit()
        return RedirectResponse(
            url="/knowledge/manage?success=Base+de+conhecimento+cadastrada+com+sucesso!",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except (DomainValidationError, EmptyKnowledgeContentError, EntityNotFoundError, ResourceOwnershipError) as exc:
        db.rollback()
        return RedirectResponse(
            url=f"/knowledge/manage?error={exc}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@web_knowledge_router.post("/knowledge/manage/{source_id}/delete", response_model=None)
async def delete_knowledge_source_web(
    source_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Exclui uma fonte de conhecimento e seus chunks associados."""
    source_repo = SqlAlchemyKnowledgeSourceRepository(db)
    chunk_repo = SqlAlchemyKnowledgeChunkRepository(db)
    topic_repo = SqlAlchemyTopicRepository(db)
    subject_repo = SqlAlchemySubjectRepository(db)

    use_case = DeleteKnowledgeSourceUseCase(
        source_repo=source_repo,
        chunk_repo=chunk_repo,
        topic_repo=topic_repo,
        subject_repo=subject_repo,
    )

    try:
        await use_case.execute(user_id=current_user.id, source_id=source_id)
        db.commit()
        return RedirectResponse(
            url="/knowledge/manage?success=Material+didático+removido+com+sucesso.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:
        db.rollback()
        return RedirectResponse(
            url=f"/knowledge/manage?error={exc}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
