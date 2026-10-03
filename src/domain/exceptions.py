"""Exceções de domínio do Study Reviewer (Clean Architecture - Camada 1).

Exceções puras de Python sem dependências externas.
"""


class DomainException(Exception):
    """Exceção base para todas as violações de regras do domínio."""


class DomainValidationError(DomainException):
    """Violação de invariantes de dados ou regras de formatação das entidades."""


class EntityNotFoundError(DomainException):
    """Entidade não encontrada para o identificador fornecido."""


class EmptyPoolError(DomainException):
    """Tentativa de iniciar estudo em uma matéria ou tema sem nenhum flashcard."""


class DuplicateEntityError(DomainException):
    """Tentativa de cadastrar uma entidade com nome ou identificador duplicado no mesmo escopo."""
