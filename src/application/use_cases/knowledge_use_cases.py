"""Casos de uso para gestão de materiais didáticos locais."""

from uuid import UUID

import nh3

from src.application.dto.knowledge_dto import (
    CreateKnowledgeSourceRequest,
    KnowledgeSourceResponse,
    LinkKnowledgeSourceRequest,
)
from src.application.ports.repositories import (
    IKnowledgeSourceRepository,
    ISubjectRepository,
    ITopicRepository,
)
from src.domain.entities import KnowledgeSource
from src.domain.exceptions import (
    DomainValidationError,
    EmptyKnowledgeContentError,
    EntityNotFoundError,
    KnowledgeSourceNotFoundError,
    ResourceOwnershipError,
)


class IngestKnowledgeSourceUseCase:
    """Caso de uso para ingestão e sanitização local de materiais didáticos."""

    def __init__(
        self,
        source_repo: IKnowledgeSourceRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._source_repo = source_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    async def execute(
        self,
        user_id: UUID,
        topic_id: UUID | None,
        request: CreateKnowledgeSourceRequest,
    ) -> KnowledgeSourceResponse:
        target_topic_ids: list[UUID] = list(request.topic_ids) if request.topic_ids else []
        if not target_topic_ids and topic_id is not None:
            target_topic_ids = [topic_id]

        if not target_topic_ids:
            raise DomainValidationError(
                "O material didático deve estar associado a pelo menos 1 tema."
            )

        for t_id in target_topic_ids:
            topic = self._topic_repo.get_by_id(t_id)
            if not topic:
                raise EntityNotFoundError("Tema não encontrado.")

            subject = self._subject_repo.get_by_id(topic.subject_id)
            if not subject or not subject.can_be_edited_by(user_id):
                raise ResourceOwnershipError(
                    "Apenas o proprietário da matéria pode cadastrar materiais didáticos."
                )

        # Sanitização defensiva do conteúdo
        cleaned_content = nh3.clean(request.content.strip(), tags=set()).strip()
        if len(cleaned_content) < 20:
            raise EmptyKnowledgeContentError(
                "O conteúdo do material deve ter pelo menos 20 caracteres úteis."
            )

        # Criação da entidade fonte com suporte a múltiplos temas (100% local/offline)
        source = KnowledgeSource(
            title=request.title,
            topic_ids=tuple(target_topic_ids),
            content_type=request.content_type,
            total_chunks=0,
            char_count=len(cleaned_content),
            raw_text=cleaned_content,
        )
        saved_source = self._source_repo.save(source)

        return KnowledgeSourceResponse(
            id=saved_source.id,
            topic_id=saved_source.topic_id,
            title=saved_source.title,
            content_type=saved_source.content_type,
            total_chunks=saved_source.total_chunks,
            char_count=saved_source.char_count,
            created_at=saved_source.created_at.isoformat(),
            topic_ids=list(saved_source.topic_ids),
        )


class LinkKnowledgeSourceToTopicsUseCase:
    """Caso de uso para atualizar a associação N:N de temas de uma fonte de conhecimento."""

    def __init__(
        self,
        source_repo: IKnowledgeSourceRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._source_repo = source_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    async def execute(
        self,
        user_id: UUID,
        request: LinkKnowledgeSourceRequest,
    ) -> KnowledgeSourceResponse:
        source = self._source_repo.get_by_id(request.source_id)
        if not source:
            raise KnowledgeSourceNotFoundError("Fonte de conhecimento não encontrada.")

        if not request.topic_ids:
            raise DomainValidationError("A fonte deve estar associada a pelo menos 1 tema.")

        for t_id in request.topic_ids:
            topic = self._topic_repo.get_by_id(t_id)
            if not topic:
                raise EntityNotFoundError("Tema não encontrado.")
            subject = self._subject_repo.get_by_id(topic.subject_id)
            if not subject or not subject.can_be_edited_by(user_id):
                raise ResourceOwnershipError(
                    "Apenas o proprietário da matéria pode gerenciar fontes de conhecimento."
                )

        updated_source = KnowledgeSource(
            id=source.id,
            title=source.title,
            topic_ids=tuple(request.topic_ids),
            content_type=source.content_type,
            total_chunks=source.total_chunks,
            char_count=source.char_count,
            raw_text=source.raw_text,
            node_id=source.node_id,
            created_at=source.created_at,
        )
        saved = self._source_repo.save(updated_source)
        return KnowledgeSourceResponse(
            id=saved.id,
            topic_id=saved.topic_id,
            title=saved.title,
            content_type=saved.content_type,
            total_chunks=saved.total_chunks,
            char_count=saved.char_count,
            created_at=saved.created_at.isoformat(),
            topic_ids=list(saved.topic_ids),
        )


class GetTopicKnowledgeSourcesUseCase:
    """Caso de uso para listagem dos materiais didáticos cadastrados em um tema."""

    def __init__(
        self,
        source_repo: IKnowledgeSourceRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._source_repo = source_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    async def execute(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> list[KnowledgeSourceResponse]:
        topic = self._topic_repo.get_by_id(topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_studied_by(user_id):
            raise ResourceOwnershipError("Sem permissão para visualizar o tema.")

        sources = self._source_repo.list_by_topic(topic_id)
        return [
            KnowledgeSourceResponse(
                id=s.id,
                topic_id=s.topic_id,
                title=s.title,
                content_type=s.content_type,
                total_chunks=s.total_chunks,
                char_count=s.char_count,
                created_at=s.created_at.isoformat(),
                topic_ids=list(s.topic_ids),
            )
            for s in sources
        ]


class DeleteKnowledgeSourceUseCase:
    """Caso de uso para remoção de um material didático."""

    def __init__(
        self,
        source_repo: IKnowledgeSourceRepository,
        topic_repo: ITopicRepository,
        subject_repo: ISubjectRepository,
    ) -> None:
        self._source_repo = source_repo
        self._topic_repo = topic_repo
        self._subject_repo = subject_repo

    async def execute(self, user_id: UUID, source_id: UUID) -> None:
        source = self._source_repo.get_by_id(source_id)
        if not source:
            raise KnowledgeSourceNotFoundError("Fonte de conhecimento não encontrada.")

        topic = self._topic_repo.get_by_id(source.topic_id)
        if not topic:
            raise EntityNotFoundError("Tema não encontrado.")

        subject = self._subject_repo.get_by_id(topic.subject_id)
        if not subject or not subject.can_be_edited_by(user_id):
            raise ResourceOwnershipError("Apenas o proprietário pode excluir materiais didáticos.")

        self._source_repo.delete(source_id)
