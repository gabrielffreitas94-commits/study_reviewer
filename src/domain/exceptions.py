"""Exceções de domínio do Study Reviewer (Clean Architecture - Camada 1).

Exceções puras de Python sem dependências externas.
"""


class DomainException(Exception):
    """Exceção base para todas as violações de regras do domínio."""


class DomainValidationError(DomainException):
    """Violação de invariantes de dados ou regras de formatação das entidades."""


class InvalidEmailError(DomainValidationError):
    """Formato de endereço de e-mail inválido segundo o padrão RFC 5322."""


class InvalidGoogleSubError(DomainValidationError):
    """Identificador Google sub nulo, vazio ou inválido."""


class EntityNotFoundError(DomainException):
    """Entidade não encontrada para o identificador fornecido."""


class EmptyPoolError(DomainException):
    """Tentativa de iniciar estudo em uma matéria ou tema sem nenhum flashcard."""


class DuplicateEntityError(DomainException):
    """Tentativa de cadastrar uma entidade com nome ou identificador duplicado no mesmo escopo."""


class UnauthorizedError(DomainException):
    """Tentativa de operação sem autenticação válida ou com sessão expirada."""


class ResourceOwnershipError(DomainException):
    """Tentativa de acesso, edição ou exclusão de recurso pertencente a outro usuário (IDOR)."""


class InvalidSessionTokenError(DomainException):
    """Token de sessão com formato inválido, assinatura violada ou decifração corrompida."""
