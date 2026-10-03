"""Camada de Domínio do Study Reviewer (Clean Architecture - Camada 1)."""

from src.domain.entities import Flashcard, FlashcardPoolSession, Subject, Topic
from src.domain.exceptions import (
    DomainException,
    DomainValidationError,
    DuplicateEntityError,
    EmptyPoolError,
    EntityNotFoundError,
)
from src.domain.protocols import IRandomGenerator
from src.domain.services import FlashcardPoolService

__all__ = [
    "DomainException",
    "DomainValidationError",
    "DuplicateEntityError",
    "EmptyPoolError",
    "EntityNotFoundError",
    "Flashcard",
    "FlashcardPoolSession",
    "FlashcardPoolService",
    "IRandomGenerator",
    "Subject",
    "Topic",
]
