"""Controladores Web para o Hub de Desempenho e Auditoria com Jinja2 e HTMX (Sprint 04).

Camada 3 - Adaptadores.
"""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyReviewAuditRepository,
    SqlAlchemySubjectRepository,
    SqlAlchemyUserRepository,
)
from src.application.use_cases.performance_use_cases import (
    ExportUserDataUseCase,
    GetUserStudyStatisticsUseCase,
    ListUserReviewAuditLogsUseCase,
)
from src.domain.entities import User
from src.domain.exceptions import DomainValidationError, EntityNotFoundError
from src.infrastructure.clock import system_clock
from src.infrastructure.database import get_db
from src.infrastructure.security.dependencies import get_current_user

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

web_performance_router = APIRouter()


@web_performance_router.get("/performance", response_class=HTMLResponse)
def get_performance_hub(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Renderiza a página principal do Hub de Desempenho e Auditoria Histórica."""
    audit_repo = SqlAlchemyReviewAuditRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)
    subj_repo = SqlAlchemySubjectRepository(db)

    stats_use_case = GetUserStudyStatisticsUseCase(audit_repo=audit_repo, progress_repo=prog_repo)
    stats = stats_use_case.execute(user_id=current_user.id)

    logs_use_case = ListUserReviewAuditLogsUseCase(audit_repo=audit_repo)
    initial_logs = logs_use_case.execute(user_id=current_user.id, page=1, page_size=10)

    user_subjects = subj_repo.list_accessible(current_user.id)
    pending_questions_count = prog_repo.count_due_questions(current_user.id, system_clock.today())

    return templates.TemplateResponse(
        request=request,
        name="performance/performance_hub.html",
        context={
            "current_user": current_user,
            "stats": stats,
            "logs": initial_logs,
            "subjects": user_subjects,
            "pending_questions_count": pending_questions_count,
            "selected_subject_id": None,
        },
    )


@web_performance_router.get("/performance/audit-logs", response_class=HTMLResponse)
def get_audit_logs_partial(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    subject_id: Annotated[UUID | None, Query()] = None,
) -> Response:
    """Retorna partial HTMX da tabela de logs de auditoria com paginação reativa."""
    audit_repo = SqlAlchemyReviewAuditRepository(db)
    logs_use_case = ListUserReviewAuditLogsUseCase(audit_repo=audit_repo)

    try:
        logs = logs_use_case.execute(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            subject_id=subject_id,
        )
    except DomainValidationError as exc:
        return HTMLResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f"<div class='p-4 bg-rose-50 text-rose-800 rounded-xl'>{exc}</div>",
        )

    return templates.TemplateResponse(
        request=request,
        name="performance/_audit_table_partial.html",
        context={
            "logs": logs,
            "selected_subject_id": subject_id,
        },
    )


@web_performance_router.get("/performance/export")
def export_user_data_web(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    format_type: Annotated[str, Query(alias="format")] = "csv",
) -> StreamingResponse:
    """Download de arquivo de portabilidade de dados (LGPD Art. 18) via streaming O(1)."""
    user_repo = SqlAlchemyUserRepository(db)
    audit_repo = SqlAlchemyReviewAuditRepository(db)
    q_repo = SqlAlchemyQuestionRepository(db)

    use_case = ExportUserDataUseCase(
        user_repo=user_repo,
        audit_repo=audit_repo,
        question_repo=q_repo,
        clock=system_clock,
    )

    try:
        stream, filename, media_type = use_case.execute(
            user_id=current_user.id,
            format_type=format_type,
        )
        return StreamingResponse(
            stream,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Content-Type-Options": "nosniff",
            },
        )
    except (DomainValidationError, EntityNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
