"""Controladores de API REST para Estatísticas, Auditoria e Exportação LGPD (Sprint 04).

Camada 3 - Adaptadores.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.adapters.persistence.repositories import (
    SqlAlchemyQuestionProgressRepository,
    SqlAlchemyQuestionRepository,
    SqlAlchemyReviewAuditRepository,
    SqlAlchemyUserRepository,
)
from src.application.dto.performance_dto import PaginatedAuditLogsDTO, UserStatisticsDTO
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

api_performance_router = APIRouter(prefix="/api/v1/performance", tags=["Performance & Audit"])


@api_performance_router.get("/statistics", response_model=UserStatisticsDTO)
def get_user_statistics_api(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserStatisticsDTO:
    """Retorna KPIs consolidados, distribuição da pirâmide SRS e linha do tempo de retenção."""
    audit_repo = SqlAlchemyReviewAuditRepository(db)
    prog_repo = SqlAlchemyQuestionProgressRepository(db)

    use_case = GetUserStudyStatisticsUseCase(audit_repo=audit_repo, progress_repo=prog_repo)
    return use_case.execute(user_id=current_user.id)


@api_performance_router.get("/audit-logs", response_model=PaginatedAuditLogsDTO)
def list_user_audit_logs_api(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1, description="Número da página (1-indexado)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Registros por página")] = 10,
    subject_id: Annotated[UUID | None, Query(description="Filtro opcional por matéria")] = None,
) -> PaginatedAuditLogsDTO:
    """Lista o histórico indelével de revisões do estudante com paginação e filtro anti-IDOR."""
    audit_repo = SqlAlchemyReviewAuditRepository(db)
    use_case = ListUserReviewAuditLogsUseCase(audit_repo=audit_repo)

    try:
        return use_case.execute(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            subject_id=subject_id,
        )
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_performance_router.get("/export")
def export_user_data_api(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    format_type: Annotated[str, Query(alias="format", description="Formato (csv ou json)")] = "csv",
) -> StreamingResponse:
    """Exporta todos os dados do titular em streaming O(1) conforme LGPD Art. 18."""
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
