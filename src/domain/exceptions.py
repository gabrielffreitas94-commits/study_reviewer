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


class StudySessionError(DomainException):
    """Exceção base para o subsistema de sessões de estudo."""


class SessionExpiredError(StudySessionError):
    """Sessão efêmera expirou no cache após 24h de inatividade."""


class SessionQueueEmptyError(StudySessionError):
    """Fila de cards da matéria/tópico esgotada ou sem registros."""


class SessionDesynchronizedError(StudySessionError):
    """Inconsistência detectada entre cursor local e estado remoto."""


class InvalidScoreError(DomainValidationError):
    """Nota informada fora do intervalo fechado [0, 100]."""


class QuestionNotFoundError(EntityNotFoundError):
    """Pergunta aberta não encontrada para o identificador fornecido."""


class QuestionNotDueError(DomainException):
    """Tentativa de revisar pergunta com agendamento futuro (anti-exploit temporal)."""


class InvalidPromptError(DomainValidationError):
    """Enunciado de pergunta vazio ou ultrapassando 10.000 caracteres."""


class InvalidExpectedAnswerError(DomainValidationError):
    """Gabarito de pergunta vazio ou ultrapassando 10.000 caracteres."""


class KnowledgeSourceNotFoundError(EntityNotFoundError):
    """Fonte de conhecimento não encontrada para o identificador fornecido."""


class EmptyKnowledgeContentError(DomainValidationError):
    """Conteúdo textual de conhecimento ou chunk vazio ou insuficiente."""


class InvalidEmbeddingError(DomainValidationError):
    """Vetor de embedding com formato inválido, nulo ou dimensões incorretas."""
