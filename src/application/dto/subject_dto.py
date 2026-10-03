"""DTOs para Matérias (Clean Architecture - Camada 2)."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class CreateSubjectDTO:
    """Dados de entrada para criação de Matéria."""

    name: str


@dataclass(frozen=True)
class SubjectDTO:
    """Dados de saída representando uma Matéria."""

    id: UUID
    name: str
    created_at: date
