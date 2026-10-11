"""DTOs para Matérias (Clean Architecture - Camada 2)."""

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CreateSubjectDTO:
    """Dados de entrada para criação de Matéria."""

    name: str
    is_public: bool = False


@dataclass(frozen=True)
class SubjectDTO:
    """Dados de saída representando uma Matéria."""

    id: UUID
    name: str
    created_at: date
    owner_id: UUID = field(default_factory=uuid4)
    is_public: bool = False
    is_owner: bool = True
