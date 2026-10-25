"""Data Transfer Objects (DTOs) da Árvore de Estudos RPG (Clean Architecture - Camada 2)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CreateStudyMapDTO:
    """DTO de entrada para criação de mapa ou sub-mapa."""

    title: str
    description: str | None = None
    is_public: bool = False
    parent_node_id: UUID | None = None


@dataclass(slots=True, frozen=True)
class StudyMapDTO:
    """DTO de saída representando os metadados de um mapa de estudo."""

    id: UUID
    owner_id: UUID
    title: str
    description: str | None
    is_public: bool
    parent_node_id: UUID | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True, frozen=True)
class CreateStudyNodeDTO:
    """DTO de entrada para criação de nó no canvas."""

    title: str
    description: str | None = None
    pos_x: float = 0.0
    pos_y: float = 0.0
    icon: str = "brain"


@dataclass(slots=True, frozen=True)
class UpdateStudyNodeDTO:
    """DTO de atualização de propriedades de um nó."""

    title: str | None = None
    description: str | None = None
    icon: str | None = None


@dataclass(slots=True, frozen=True)
class NodePositionDTO:
    """DTO de posicionamento individual no canvas para atualizações em lote."""

    node_id: UUID
    pos_x: float
    pos_y: float


@dataclass(slots=True, frozen=True)
class ConnectNodesDTO:
    """DTO de criação de aresta de pré-requisito."""

    source_node_id: UUID
    target_node_id: UUID


@dataclass(slots=True, frozen=True)
class StudyEdgeDTO:
    """DTO de saída para aresta de pré-requisito no grafo."""

    id: UUID
    map_id: UUID
    source_node_id: UUID
    target_node_id: UUID


@dataclass(slots=True, frozen=True)
class StudyNodeDTO:
    """DTO de nó com estado dinâmico de nível SRS e desbloqueio."""

    id: UUID
    map_id: UUID
    title: str
    description: str | None
    pos_x: float
    pos_y: float
    icon: str
    effective_level: int
    is_unlocked: bool
    overdue_questions_count: int
    has_submap: bool
    materials_count: int
    questions_count: int
    flashcards_count: int


@dataclass(slots=True, frozen=True)
class StudyGraphDTO:
    """DTO do grafo completo para renderização no Canvas RPG."""

    map: StudyMapDTO
    nodes: list[StudyNodeDTO]
    edges: list[StudyEdgeDTO]


@dataclass(slots=True, frozen=True)
class NodeStudyHubDTO:
    """DTO com todo o conteúdo agrupado de um nó para sessão de estudo ativo."""

    node: StudyNodeDTO
    materials: list[dict[str, object]]
    due_questions: list[dict[str, object]]
    all_questions: list[dict[str, object]]
    flashcards: list[dict[str, object]]
