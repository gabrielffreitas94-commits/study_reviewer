"""Camada de Domínio do Study Reviewer (Clean Architecture - Camada 1)."""

from src.domain.entities import (
    Flashcard,
    FlashcardPoolSession,
    StudyEdge,
    StudyMap,
    StudyNode,
    Subject,
    Topic,
    UserNodeProgress,
)
from src.domain.exceptions import (
    CrossMapEdgeError,
    CyclicDependencyError,
    DomainException,
    DomainValidationError,
    DuplicateEntityError,
    EmptyPoolError,
    EntityNotFoundError,
    SelfReferencingEdgeError,
    StudyEdgeNotFoundError,
    StudyMapNotFoundError,
    StudyNodeNotFoundError,
)
from src.domain.protocols import IRandomGenerator
from src.domain.services import (
    DAGValidatorService,
    FlashcardPoolService,
    StudyTreeProgressionService,
)

__all__ = [
    "CrossMapEdgeError",
    "CyclicDependencyError",
    "DAGValidatorService",
    "DomainException",
    "DomainValidationError",
    "DuplicateEntityError",
    "EmptyPoolError",
    "EntityNotFoundError",
    "Flashcard",
    "FlashcardPoolService",
    "FlashcardPoolSession",
    "IRandomGenerator",
    "SelfReferencingEdgeError",
    "StudyEdge",
    "StudyEdgeNotFoundError",
    "StudyMap",
    "StudyMapNotFoundError",
    "StudyNode",
    "StudyNodeNotFoundError",
    "StudyTreeProgressionService",
    "Subject",
    "Topic",
    "UserNodeProgress",
]
