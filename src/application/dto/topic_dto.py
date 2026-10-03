"""DTOs para Temas (Clean Architecture - Camada 2)."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class CreateTopicDTO:
    """Dados de entrada para criação de Tema."""

    subject_id: UUID
    name: str


@dataclass(frozen=True)
class TopicDTO:
    """Dados de saída representando um Tema."""

    id: UUID
    subject_id: UUID
    name: str
    created_at: date
