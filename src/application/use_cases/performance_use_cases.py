"""Casos de uso para o módulo de Performance, Auditoria e Exportação LGPD (Sprint 04)."""

import json
import logging
import math
from collections.abc import Iterator
from datetime import date
from uuid import UUID

from src.application.dto.performance_dto import (
    DailyActivityDataPointDTO,
    DailyMatureDataPointDTO,
    PaginatedAuditLogsDTO,
    ReviewAuditLogDTO,
    SubjectPerformanceDTO,
    UserStatisticsDTO,
)
from src.application.ports.repositories import (
    IClockService,
    IQuestionProgressRepository,
    IQuestionRepository,
    IReviewAuditRepository,
    IUserRepository,
)
from src.domain.entities import User
from src.domain.exceptions import DomainValidationError, EntityNotFoundError
from src.domain.services import StudyStatisticsCalculatorService

logger = logging.getLogger(__name__)

# Caracteres de risco para CSV Formula Injection (CWE-1236)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_cell(value: str) -> str:
    """Sanitiza e formata uma célula para CSV (RFC 4180) e previne Formula Injection (CWE-1236).

    Regras:
    1. Se o valor iniciar por '=', '+', '-', '@', '\\t' ou '\\r', prefixa com apóstrofo (').
    2. Escapa aspas duplas internas duplicando-as (ex: '"' -> '""').
    3. Envolve o valor resultante entre aspas duplas.
    """
    if not value:
        return '""'
    sanitized = f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value
    escaped = sanitized.replace('"', '""')
    return f'"{escaped}"'


class GetUserStudyStatisticsUseCase:
    """Caso de uso para calcular KPIs consolidados e evolução temporal do estudante."""

    def __init__(
        self,
        audit_repo: IReviewAuditRepository,
        progress_repo: IQuestionProgressRepository,
    ) -> None:
        self._audit_repo = audit_repo
        self._progress_repo = progress_repo

    def execute(self, user_id: UUID) -> UserStatisticsDTO:
        logs = self._audit_repo.get_all_by_user(user_id)
        progresses = self._progress_repo.list_by_user(user_id)

        computed = StudyStatisticsCalculatorService.compute_metrics(
            logs=logs,
            progresses=progresses,
        )

        subject_dtos = [
            SubjectPerformanceDTO(
                subject_name=sp.subject_name,
                total_reviews=sp.total_reviews,
                perfect_reviews=sp.perfect_reviews,
                retention_rate=sp.retention_rate,
            )
            for sp in computed.subject_performances
        ]

        mature_timeline_dtos = [
            DailyMatureDataPointDTO(
                date=dp.date,
                mature_count=dp.mature_count,
            )
            for dp in computed.mature_evolution_timeline
        ]

        # Agrupamento diário de atividade
        activity_by_date: dict[date, int] = {}
        for log in logs:
            activity_by_date[log.review_date] = activity_by_date.get(log.review_date, 0) + 1

        reviews_activity_dtos = [
            DailyActivityDataPointDTO(
                date=review_date,
                reviews_count=count,
            )
            for review_date, count in sorted(activity_by_date.items())
        ]

        return UserStatisticsDTO(
            retention_rate=computed.retention_rate,
            mature_questions_count=computed.mature_questions_count,
            total_reviews_count=computed.total_reviews_count,
            active_days_count=computed.active_days_count,
            srs_distribution=computed.srs_distribution,
            subject_performances=subject_dtos,
            mature_evolution_timeline=mature_timeline_dtos,
            reviews_activity_timeline=reviews_activity_dtos,
        )


class ListUserReviewAuditLogsUseCase:
    """Caso de uso para listagem paginada de histórico de revisões com proteção anti-IDOR."""

    def __init__(self, audit_repo: IReviewAuditRepository) -> None:
        self._audit_repo = audit_repo

    def execute(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 10,
        subject_id: UUID | None = None,
    ) -> PaginatedAuditLogsDTO:
        if page < 1:
            raise DomainValidationError("O número da página deve ser maior ou igual a 1")
        if page_size < 1 or page_size > 100:
            raise DomainValidationError("O tamanho da página deve estar entre 1 e 100")

        offset = (page - 1) * page_size
        logs = self._audit_repo.list_by_user(
            user_id=user_id,
            limit=page_size,
            offset=offset,
            subject_id=subject_id,
        )
        total_items = self._audit_repo.count_by_user(
            user_id=user_id,
            subject_id=subject_id,
        )
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

        dtos = [
            ReviewAuditLogDTO(
                id=log.id,
                question_id=log.question_id,
                subject_id=log.subject_id,
                topic_id=log.topic_id,
                historical_subject_name=log.historical_subject_name,
                historical_topic_name=log.historical_topic_name,
                review_date=log.review_date,
                score=log.score,
                level_before=log.level_before,
                level_after=log.level_after,
                is_promoted=log.is_promoted,
                is_regressed=log.is_regressed,
                evaluation_mode=log.evaluation_mode,
                logged_at=log.logged_at,
            )
            for log in logs
        ]

        return PaginatedAuditLogsDTO(
            items=dtos,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )


class ExportUserDataUseCase:
    """Caso de uso para exportação de dados do titular (LGPD Art. 18) via streaming O(1)."""

    def __init__(
        self,
        user_repo: IUserRepository,
        audit_repo: IReviewAuditRepository,
        question_repo: IQuestionRepository,
        clock: IClockService,
    ) -> None:
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._question_repo = question_repo
        self._clock = clock

    def execute(
        self,
        user_id: UUID,
        format_type: str,
    ) -> tuple[Iterator[str], str, str]:
        normalized_format = format_type.lower().strip()
        if normalized_format not in ("csv", "json"):
            raise DomainValidationError(
                f"Formato de exportação inválido: '{format_type}'. "
                "Formatos suportados: 'csv', 'json'."
            )

        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("Usuário não encontrado.")

        today_str = self._clock.today().strftime("%Y%m%d")
        filename = f"study_reviewer_export_{today_str}.{normalized_format}"

        if normalized_format == "csv":
            media_type = "text/csv; charset=utf-8"
            stream = self._generate_csv(user_id)
        else:
            media_type = "application/json; charset=utf-8"
            stream = self._generate_json(user)

        return stream, filename, media_type

    def _generate_csv(self, user_id: UUID) -> Iterator[str]:
        # BOM UTF-8 para compatibilidade perfeita no Microsoft Excel
        yield "\ufeff"
        # Cabeçalho RFC 4180
        yield (
            "ID_Revisao,Data_Revisao,Materia,Tema,Pergunta,Nota,"
            "Nivel_Anterior,Novo_Nivel,Modo_Avaliacao,Timestamp\r\n"
        )

        for log in self._audit_repo.stream_by_user(user_id):
            question_prompt = ""
            if log.question_id:
                q = self._question_repo.get_by_id(log.question_id)
                if q:
                    question_prompt = q.prompt

            line = (
                f"{log.id},"
                f"{log.review_date.isoformat()},"
                f"{_sanitize_csv_cell(log.historical_subject_name)},"
                f"{_sanitize_csv_cell(log.historical_topic_name)},"
                f"{_sanitize_csv_cell(question_prompt)},"
                f"{log.score},"
                f"{log.level_before},"
                f"{log.level_after},"
                f"{_sanitize_csv_cell(log.evaluation_mode)},"
                f"{log.logged_at.isoformat() if log.logged_at else ''}\r\n"
            )
            yield line

    def _generate_json(self, user: User) -> Iterator[str]:
        yield '{\n  "user": '
        user_data = {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat()
            if hasattr(user, "created_at") and user.created_at
            else None,
        }
        yield json.dumps(user_data, ensure_ascii=False)
        yield ',\n  "review_logs": [\n'

        is_first = True
        for log in self._audit_repo.stream_by_user(user.id):
            if not is_first:
                yield ",\n"
            else:
                is_first = False

            log_dict = {
                "id": str(log.id),
                "question_id": str(log.question_id) if log.question_id else None,
                "historical_subject_name": log.historical_subject_name,
                "historical_topic_name": log.historical_topic_name,
                "review_date": log.review_date.isoformat(),
                "score": log.score,
                "level_before": log.level_before,
                "level_after": log.level_after,
                "evaluation_mode": log.evaluation_mode,
                "logged_at": log.logged_at.isoformat() if log.logged_at else None,
            }
            yield f"    {json.dumps(log_dict, ensure_ascii=False)}"

        yield "\n  ]\n}"
