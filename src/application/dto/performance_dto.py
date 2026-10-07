"""DTOs para o módulo de Performance, Auditoria e Estatísticas de Estudo (Sprint 04)."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class SubjectPerformanceDTO:
    """Métrica de desempenho agregada por matéria histórica."""

    subject_name: str
    total_reviews: int
    perfect_reviews: int
    retention_rate: float


@dataclass(slots=True, frozen=True)
class DailyMatureDataPointDTO:
    """Ponto de dado na linha do tempo de Retenção Madura (Nível 4+)."""

    date: date
    mature_count: int


@dataclass(slots=True, frozen=True)
class DailyActivityDataPointDTO:
    """Ponto de dado na linha do tempo de atividade de revisões por dia."""

    date: date
    reviews_count: int


@dataclass(slots=True, frozen=True)
class UserStatisticsDTO:
    """Visão consolidada de KPIs e gráficos para o Hub de Desempenho."""

    retention_rate: float
    mature_questions_count: int
    total_reviews_count: int
    active_days_count: int
    srs_distribution: dict[int, int]
    subject_performances: list[SubjectPerformanceDTO]
    mature_evolution_timeline: list[DailyMatureDataPointDTO]
    reviews_activity_timeline: list[DailyActivityDataPointDTO]


@dataclass(slots=True, frozen=True)
class ReviewAuditLogDTO:
    """Item de log de auditoria histórico para visualização na tabela."""

    id: UUID
    question_id: UUID | None
    subject_id: UUID | None
    topic_id: UUID | None
    historical_subject_name: str
    historical_topic_name: str
    review_date: date
    score: int
    level_before: int
    level_after: int
    is_promoted: bool
    is_regressed: bool
    evaluation_mode: str
    logged_at: datetime | None


@dataclass(slots=True, frozen=True)
class PaginatedAuditLogsDTO:
    """Resultado paginado da lista de logs de auditoria."""

    items: list[ReviewAuditLogDTO]
    page: int
    page_size: int
    total_items: int
    total_pages: int


@dataclass(slots=True, frozen=True)
class ExportDataChunkDTO:
    """Metadados e gerador de exportação de dados."""

    filename: str
    media_type: str
